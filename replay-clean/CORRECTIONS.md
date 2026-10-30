# Setup log checksum correction (2026-10-29)

File: `replay-clean/out/bundle/logs/setup/setup-partB-20261026T054604.txt`.
Its path within the bundle manifest is `logs/setup/setup-partB-20261026T054604.txt`.

`replay-clean/out/bundle/results.json` records:

- Size: 8,647 bytes.
- SHA256: `9db966ed783c2399f244e33446c256652a7ace6a92ed62be641231602ac41998`.

The complete retained file has:

- Size: 8,684 bytes (`wc -c`).
- SHA256: `ca7a47ef4c4cd0b9cdee7079b954cf3a85ab27e03d5b58e6176835352c30a276` (`shasum -a 256`).

The prefix check, `head -c 8647 replay-clean/out/bundle/logs/setup/setup-partB-20261026T054604.txt | shasum -a 256`,
returns `9db966ed783c2399f244e33446c256652a7ace6a92ed62be641231602ac41998`,
equal to the recorded hash. The remaining 37 bytes are quoted verbatim below,
including the terminating newline:

```text
# 2026-10-26T06:06:03+0000 done rc=0
```

The trailer is the setup script's completion line, written after `results.json`
was produced. No experimental outcome, cell result or other hash is affected.
`results.json` is retained unchanged as the historical manifest.
