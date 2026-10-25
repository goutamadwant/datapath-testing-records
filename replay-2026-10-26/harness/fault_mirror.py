#!/usr/bin/env python3
"""Fault-injecting Maven mirror (reconstruction, 2026-10-25).

Reconstructed from the description in apache/seatunnel PR 12468 ("A local HTTP server served
artifacts from a warm local repository and injected the faults above for `junit` paths"). The
original server was local-only and is lost; this is a new implementation, not the original.

Serves a Maven local-repository directory over HTTP/1.1 (keep-alive, Content-Length on every
response). Checksum files (.sha1/.md5) are computed on the fly from the artifact file because a
local repository does not keep them; `maven-metadata.xml` falls back to the
`maven-metadata-<repoId>.xml` copy stored in the local repository.

Fault modes (applied per request path; a path is a fault target when it contains "/junit/" and is
not a checksum file; the first N GET requests for each target path get the fault):
  none          no fault
  503x2         HTTP 503 on the first 2 requests
  reset4        TCP reset (SO_LINGER 0, no response) on the first 4 requests
  429x2         HTTP 429 on the first 2 requests
  429x2nobody   sensitivity variant added after the primary runs: HTTP 429 with an empty body
                (Content-Length: 0) on the first 2 requests
  truncate1     first request: full Content-Length header, half the body, then the socket is closed
  wrapper429s   HTTP 429 for every request of maven-wrapper-*.jar until 30 s after the first such
                request (the "wrapper jar 429 for 30 s" case)

Every request is logged as one JSON line (monotonic and wall-clock timestamps, path, request
number for that path, action taken) to --log.
"""
import argparse
import hashlib
import json
import os
import socket
import struct
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

FAULTS = {
    "none": (None, 0),
    "503x2": ("503", 2),
    "reset4": ("reset", 4),
    "429x2": ("429", 2),
    "429x2nobody": ("429nobody", 2),
    "truncate1": ("truncate", 1),
    "wrapper429s": ("wrapper429", 30.0),
}


class State:
    def __init__(self, root, fault, logf, prefix):
        self.root = os.path.abspath(root)
        self.fault = fault
        self.logf = logf
        self.prefix = prefix.rstrip("/")
        self.counts = {}
        self.lock = threading.Lock()
        self.t0 = time.monotonic()
        self.wrapper_first = None

    def log(self, **kw):
        kw["t_rel_s"] = round(time.monotonic() - self.t0, 3)
        kw["wall"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()) + (
            ".%03d" % int((time.time() % 1) * 1000))
        with self.lock:
            self.logf.write(json.dumps(kw) + "\n")
            self.logf.flush()


def is_checksum(path):
    return path.endswith((".sha1", ".md5", ".sha256", ".sha512", ".asc"))


def make_handler(st):
    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "fault-mirror/1"

        def log_message(self, fmt, *args):  # quiet stderr; we log JSON ourselves
            pass

        def _resolve(self, rel):
            p = os.path.normpath(os.path.join(st.root, rel))
            if not p.startswith(st.root + os.sep):
                return None, None
            if os.path.isfile(p):
                return p, None
            for algo in ("sha1", "md5"):
                if p.endswith("." + algo) and os.path.isfile(p[: -len(algo) - 1]):
                    with open(p[: -len(algo) - 1], "rb") as f:
                        return None, hashlib.new(algo, f.read()).hexdigest().encode()
            if p.endswith("maven-metadata.xml"):
                d = os.path.dirname(p)
                if os.path.isdir(d):
                    for name in sorted(os.listdir(d)):
                        if name.startswith("maven-metadata-") and name.endswith(".xml"):
                            return os.path.join(d, name), None
            return None, None

        def _send(self, code, body=b"", ctype="application/octet-stream"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD" and body:
                self.wfile.write(body)

        def _reset(self):
            try:
                self.connection.setsockopt(
                    socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
            except OSError:
                pass
            self.connection.close()
            self.close_connection = True

        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            rel = path
            if st.prefix and rel.startswith(st.prefix + "/"):
                rel = rel[len(st.prefix) + 1:]
            rel = rel.lstrip("/")
            kind, n = FAULTS[st.fault]
            with st.lock:
                st.counts[path] = st.counts.get(path, 0) + 1
                count = st.counts[path]
            target = ("/junit/" in path) and not is_checksum(path)
            action = "serve"
            if kind == "wrapper429" and "/maven-wrapper-" in path and path.endswith(".jar"):
                now = time.monotonic()
                with st.lock:
                    if st.wrapper_first is None:
                        st.wrapper_first = now
                    elapsed = now - st.wrapper_first
                if elapsed < n:
                    action = "429"
            elif kind and kind != "wrapper429" and target and count <= n:
                action = kind
            fpath, synth = self._resolve(rel)
            exists = fpath is not None or synth is not None
            st.log(method=self.command, path=path, n=count, target=target, action=action,
                   exists=exists, client=self.client_address[1])
            if action == "503":
                return self._send(503, b"Service Unavailable (injected)\n", "text/plain")
            if action == "429":
                return self._send(429, b"Too Many Requests (injected)\n", "text/plain")
            if action == "429nobody":
                return self._send(429, b"", "text/plain")
            if action == "reset":
                return self._reset()
            if not exists:
                return self._send(404, b"Not Found\n", "text/plain")
            body = synth if synth is not None else open(fpath, "rb").read()
            if action == "truncate":
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body[: len(body) // 2])
                self.wfile.flush()
                try:
                    self.connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                self.connection.close()
                self.close_connection = True
                return
            ctype = "application/xml" if path.endswith((".pom", ".xml")) else "application/octet-stream"
            self._send(200, body, ctype)

    return H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="warm Maven local repository to serve")
    ap.add_argument("--fault", required=True, choices=sorted(FAULTS))
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--prefix", default="/maven2")
    ap.add_argument("--log", required=True)
    ap.add_argument("--port-file", required=True)
    a = ap.parse_args()
    logf = open(a.log, "a")
    st = State(a.root, a.fault, logf, a.prefix)
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(st))
    srv.daemon_threads = True
    with open(a.port_file, "w") as f:
        f.write(str(srv.server_address[1]))
    st.log(event="start", fault=a.fault, port=srv.server_address[1], root=st.root)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        st.log(event="stop")


if __name__ == "__main__":
    sys.exit(main())
