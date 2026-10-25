/*
 * Part C harness (reconstruction, 2026-10-25, local-only, not part of any PR).
 *
 * Reconstructed from the description in apache/seatunnel PR 12481 ("Each scenario starts an
 * engine, kills its container, calls tearDown(), then starts a new container of the same engine
 * and runs fake_to_assert.conf"). The original harness was never published and is lost.
 *
 * Copied into seatunnel-e2e/seatunnel-connector-v2-e2e/connector-fake-e2e/src/test/java before
 * the build; run one method per JVM through the JUnit Platform launcher. Prints one RESULT line
 * per step so the outcome of every run is in the log.
 *
 * System properties: replay.runs (default 1), replay.jobTimeoutSec (default 150).
 */
package org.apache.seatunnel.e2e.connector.fake;

import org.apache.seatunnel.e2e.common.container.flink.Flink18Container;
import org.apache.seatunnel.e2e.common.container.spark.Spark3Container;

import org.junit.jupiter.api.Test;
import org.testcontainers.DockerClientFactory;
import org.testcontainers.containers.Container;
import org.testcontainers.containers.GenericContainer;

import com.github.dockerjava.api.DockerClient;
import com.github.dockerjava.api.command.InspectContainerResponse;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

public class ReplayKillTeardownTest {

    private static final int RUNS = Integer.getInteger("replay.runs", 1);
    private static final long JOB_TIMEOUT_SEC = Long.getLong("replay.jobTimeoutSec", 150L);

    static class ReplayFlink18 extends Flink18Container {
        GenericContainer<?> jm() {
            return jobManager;
        }

        GenericContainer<?> tm() {
            return taskManager;
        }
    }

    static class ReplaySpark3 extends Spark3Container {
        GenericContainer<?> master() {
            return master;
        }
    }

    private static void out(String s) {
        System.out.println("RESULT " + s);
        System.out.flush();
    }

    private static String oneLine(Throwable t) {
        String m = String.valueOf(t.getMessage()).replace('\n', ' ');
        if (m.length() > 300) {
            m = m.substring(0, 300) + "...";
        }
        return t.getClass().getName() + ": " + m;
    }

    private static String state(DockerClient docker, String id) {
        if (id == null) {
            return "none";
        }
        try {
            InspectContainerResponse r = docker.inspectContainerCmd(id).exec();
            return "exists running=" + r.getState().getRunning() + " status=" + r.getState().getStatus();
        } catch (Exception e) {
            return "removed";
        }
    }

    private static String ip(DockerClient docker, String id) {
        try {
            return docker.inspectContainerCmd(id).exec().getNetworkSettings().getNetworks().values()
                    .stream()
                    .map(n -> n.getIpAddress())
                    .findFirst()
                    .orElse("?");
        } catch (Exception e) {
            return "?";
        }
    }

    /** Number of TaskManagers registered at a JobManager, read from its REST API on the host. */
    private static String tmCount(GenericContainer<?> jm) {
        try {
            java.net.URL u =
                    new java.net.URL(
                            "http://" + jm.getHost() + ":" + jm.getMappedPort(8081) + "/overview");
            java.net.HttpURLConnection c = (java.net.HttpURLConnection) u.openConnection();
            c.setConnectTimeout(3000);
            c.setReadTimeout(3000);
            java.util.Scanner sc = new java.util.Scanner(c.getInputStream(), "UTF-8").useDelimiter("\\A");
            String body = sc.hasNext() ? sc.next() : "";
            java.util.regex.Matcher m =
                    java.util.regex.Pattern.compile("\"taskmanagers\":(\\d+)").matcher(body);
            return m.find() ? m.group(1) : "?";
        } catch (Exception e) {
            return "unreachable";
        }
    }

    private static void forceRemove(DockerClient docker, String id, String what) {
        if (id == null) {
            return;
        }
        try {
            docker.removeContainerCmd(id).withForce(true).exec();
            out("cleanup force-removed leftover " + what + " " + id.substring(0, 12));
        } catch (Exception e) {
            // already removed
        }
    }

    private static String runJob(Object container, String conf) throws Exception {
        ExecutorService ex = Executors.newSingleThreadExecutor();
        long t0 = System.nanoTime();
        try {
            Future<Container.ExecResult> f =
                    ex.submit(
                            () ->
                                    container instanceof ReplayFlink18
                                            ? ((ReplayFlink18) container).executeJob(conf)
                                            : ((ReplaySpark3) container).executeJob(conf));
            Container.ExecResult r = f.get(JOB_TIMEOUT_SEC, TimeUnit.SECONDS);
            long s = (System.nanoTime() - t0) / 1_000_000_000L;
            String tail = r.getStdout();
            if (r.getExitCode() != 0 && tail != null && tail.length() > 1500) {
                tail = tail.substring(tail.length() - 1500);
            }
            return "exit=" + r.getExitCode() + " seconds=" + s
                    + (r.getExitCode() != 0 ? " stdout_tail=" + String.valueOf(tail).replace('\n', ' ')
                            + " stderr_tail=" + String.valueOf(r.getStderr()).replace('\n', ' ') : "");
        } catch (TimeoutException e) {
            return "TIMEOUT after " + JOB_TIMEOUT_SEC + "s";
        } finally {
            ex.shutdownNow();
        }
    }

    @Test
    void flink118TaskManagerKilled() throws Exception {
        DockerClient docker = DockerClientFactory.instance().client();
        for (int run = 1; run <= RUNS; run++) {
            String p = "flink118 run=" + run + " ";
            ReplayFlink18 c1 = new ReplayFlink18();
            long t0 = System.nanoTime();
            c1.startUp();
            out(p + "startUp1 ok seconds=" + (System.nanoTime() - t0) / 1_000_000_000L);
            String jm1 = c1.jm().getContainerId();
            String tm1 = c1.tm().getContainerId();
            docker.killContainerCmd(tm1).exec();
            out(p + "killed taskmanager " + tm1.substring(0, 12) + " state=" + state(docker, tm1));
            try {
                c1.tearDown();
                out(p + "teardown completed");
            } catch (Throwable t) {
                out(p + "teardown threw " + oneLine(t));
            }
            out(p + "after-teardown jobmanager1=" + state(docker, jm1) + " taskmanager1="
                    + state(docker, tm1));
            ReplayFlink18 c2 = new ReplayFlink18();
            String jm2 = null;
            String tm2 = null;
            try {
                t0 = System.nanoTime();
                c2.startUp();
                jm2 = c2.jm().getContainerId();
                tm2 = c2.tm().getContainerId();
                out(p + "startUp2 ok seconds=" + (System.nanoTime() - t0) / 1_000_000_000L);
                // The TaskManager log names the JobManager only by its alias ("jobmanager"), so
                // count registered TaskManagers through each JobManager's REST API instead.
                boolean jm1Running = state(docker, jm1).contains("running=true");
                out(p + "taskmanager2 registration: taskmanagers_at_own_jm=" + tmCount(c2.jm())
                        + " taskmanagers_at_leaked_jm="
                        + (jm1Running ? tmCount(c1.jm()) : "n/a(jobmanager1 not running)")
                        + " jobmanager1=" + state(docker, jm1));
                out(p + "next job " + runJob(c2, "/fake_to_assert.conf"));
            } catch (Throwable t) {
                out(p + "startUp2/next job threw " + oneLine(t));
            } finally {
                try {
                    c2.tearDown();
                } catch (Throwable t) {
                    out(p + "teardown2 threw " + oneLine(t));
                }
                forceRemove(docker, jm1, "jobmanager1");
                forceRemove(docker, tm1, "taskmanager1");
                forceRemove(docker, jm2, "jobmanager2");
                forceRemove(docker, tm2, "taskmanager2");
            }
            out(p + "done");
        }
    }

    @Test
    void spark3MasterKilled() throws Exception {
        DockerClient docker = DockerClientFactory.instance().client();
        for (int run = 1; run <= RUNS; run++) {
            String p = "spark3 run=" + run + " ";
            ReplaySpark3 c1 = new ReplaySpark3();
            long t0 = System.nanoTime();
            c1.startUp();
            out(p + "startUp1 ok seconds=" + (System.nanoTime() - t0) / 1_000_000_000L);
            String m1 = c1.master().getContainerId();
            docker.killContainerCmd(m1).exec();
            out(p + "killed master " + m1.substring(0, 12) + " state=" + state(docker, m1));
            try {
                c1.tearDown();
                out(p + "teardown completed");
            } catch (Throwable t) {
                out(p + "teardown threw " + oneLine(t));
            }
            out(p + "after-teardown master1=" + state(docker, m1));
            ReplaySpark3 c2 = new ReplaySpark3();
            String m2 = null;
            try {
                t0 = System.nanoTime();
                c2.startUp();
                m2 = c2.master().getContainerId();
                out(p + "startUp2 ok seconds=" + (System.nanoTime() - t0) / 1_000_000_000L);
                out(p + "next job " + runJob(c2, "/fake_to_assert.conf"));
            } catch (Throwable t) {
                out(p + "startUp2/next job threw " + oneLine(t));
            } finally {
                try {
                    c2.tearDown();
                } catch (Throwable t) {
                    out(p + "teardown2 threw " + oneLine(t));
                }
                forceRemove(docker, m1, "master1");
                forceRemove(docker, m2, "master2");
            }
            out(p + "done");
        }
    }
}
