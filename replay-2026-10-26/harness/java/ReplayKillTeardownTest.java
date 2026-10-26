/*
 * Part C harness (reconstruction, first version 2026-10-25; this version 2026-10-26 adds explicit
 * teardown assertions, printed as ASSERT lines; local-only, not part of any PR).
 *
 * Reconstructed from the description in apache/seatunnel PR 12481 ("Each scenario starts an
 * engine, kills its container, calls tearDown(), then starts a new container of the same engine
 * and runs fake_to_assert.conf"). The original harness was never published and is lost.
 *
 * Copied into seatunnel-e2e/seatunnel-connector-v2-e2e/connector-fake-e2e/src/test/java before
 * the build; run one method per JVM through the JUnit Platform launcher. Prints one RESULT line
 * per step so the outcome of every run is in the log.
 *
 * System properties: replay.runs (default 1), replay.jobTimeoutSec (default 150),
 * replay.teardownBoundSec (default 60).
 *
 * Assertions (one "ASSERT <engine> run=<n> name=<name> result=PASS|FAIL expected=<..> observed=<..>"
 * line each; a FAIL is recorded, never thrown, so every run completes and every check is logged;
 * the one exception is pre_run_no_engine_containers, see below):
 *   pre_run_no_engine_containers      no container of the engine image exists before the run
 *                                     (a FAIL aborts the cell: JVM exit status 3)
 *   teardown_no_exception             tearDown() of the killed engine returned normally
 *   teardown_time_bound               tearDown() returned within replay.teardownBoundSec
 *   containers_absent_after_teardown  every container of the killed engine is gone after tearDown()
 *   new_taskmanager_at_own_jobmanager (Flink) the new TaskManager registered with the new JobManager
 *   next_job_exit_zero                the next job (fake_to_assert.conf) exited 0
 *   next_job_time_bound               the next job finished within replay.jobTimeoutSec
 *   post_run_no_leftover_containers   no container of the run exists after the harness cleanup
 * A container counts as removed only when the Docker API answers 404 (NotFoundException); any
 * other inspection error is reported as "inspect-error" and fails the absence checks. Cleanup
 * errors other than 404 are printed.
 *
 * Revision (2026-10-25, after the recorded runs): a failed pre_run_no_engine_containers check
 * aborts the cell. The harness prints "RESULT <engine> run=<n> aborted: ..." and exits the JVM
 * with status 3 before starting any container, so a container it did not create is never
 * started next to, inspected as, or removed as one of its own. Each test method also prints
 * "RESULT testcontainers_session=<id>", the Testcontainers session label of the containers this
 * JVM creates; part_c.sh removes leftovers only if they carry that label. The harness itself
 * force-removes only the container ids it obtained from the containers it started.
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
    private static final long TEARDOWN_BOUND_SEC = Long.getLong("replay.teardownBoundSec", 60L);
    private static final String FLINK_IMAGE = "tyrantlucifer/flink:1.18.0-scala_2.12_hadoop27";
    private static final String SPARK_IMAGE = "tyrantlucifer/spark:3.3.0";

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

    /** Pre-run safety check failed: record it and stop the JVM before any container is started. */
    private static void abort(String engine, int run, String reason) {
        System.out.println("RESULT " + engine + " run=" + run + " aborted: " + reason.replace('\n', ' '));
        System.out.flush();
        System.exit(3);
    }

    private static void session() {
        System.out.println("RESULT testcontainers_session=" + DockerClientFactory.SESSION_ID);
        System.out.flush();
    }

    private static void check(String engine, int run, String name, boolean ok, String expected,
            String observed) {
        System.out.println("ASSERT " + engine + " run=" + run + " name=" + name + " result="
                + (ok ? "PASS" : "FAIL") + " expected=" + expected.replace(' ', '_')
                + " observed=" + observed.replace(' ', '_'));
        System.out.flush();
    }

    /** Containers (any state) created from the given image. */
    private static java.util.List<String> engineContainers(DockerClient docker, String image) {
        java.util.List<String> ids = new java.util.ArrayList<>();
        for (com.github.dockerjava.api.model.Container c :
                docker.listContainersCmd().withShowAll(true).exec()) {
            if (image.equals(c.getImage())) {
                ids.add(c.getId().substring(0, 12) + ":" + c.getState());
            }
        }
        return ids;
    }

    private static boolean absent(DockerClient docker, String id) {
        return id == null || "removed".equals(state(docker, id));
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
        } catch (com.github.dockerjava.api.exception.NotFoundException e) {
            // only a 404 from the Docker API counts as removal
            return "removed";
        } catch (Exception e) {
            return "inspect-error " + e.getClass().getSimpleName();
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
        } catch (com.github.dockerjava.api.exception.NotFoundException e) {
            // already removed
        } catch (Exception e) {
            out("cleanup error " + what + " " + id.substring(0, 12) + " " + oneLine(e));
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

    private static boolean jobExitZero(String r) {
        return r.startsWith("exit=0 ");
    }

    private static String jobSeconds(String r) {
        java.util.regex.Matcher m = java.util.regex.Pattern.compile("seconds=(\\d+)").matcher(r);
        return m.find() ? m.group(1) : "none";
    }

    private static boolean jobWithinBound(String r) {
        String s = jobSeconds(r);
        return !r.startsWith("TIMEOUT") && !"none".equals(s) && Long.parseLong(s) <= JOB_TIMEOUT_SEC;
    }

    @Test
    void flink118TaskManagerKilled() throws Exception {
        DockerClient docker = DockerClientFactory.instance().client();
        final String e = "flink118";
        session();
        for (int run = 1; run <= RUNS; run++) {
            String p = "flink118 run=" + run + " ";
            java.util.List<String> pre = engineContainers(docker, FLINK_IMAGE);
            check(e, run, "pre_run_no_engine_containers", pre.isEmpty(), "none", pre.toString());
            if (!pre.isEmpty()) {
                abort(e, run, "containers of " + FLINK_IMAGE + " exist before the run " + pre);
            }
            ReplayFlink18 c1 = new ReplayFlink18();
            long t0 = System.nanoTime();
            c1.startUp();
            out(p + "startUp1 ok seconds=" + (System.nanoTime() - t0) / 1_000_000_000L);
            String jm1 = c1.jm().getContainerId();
            String tm1 = c1.tm().getContainerId();
            docker.killContainerCmd(tm1).exec();
            out(p + "killed taskmanager " + tm1.substring(0, 12) + " state=" + state(docker, tm1));
            boolean threw = false;
            String thrown = "none";
            t0 = System.nanoTime();
            try {
                c1.tearDown();
                out(p + "teardown completed");
            } catch (Throwable t) {
                threw = true;
                thrown = oneLine(t);
                out(p + "teardown threw " + thrown);
            }
            long tdMs = (System.nanoTime() - t0) / 1_000_000L;
            out(p + "teardown millis=" + tdMs);
            String jm1s = state(docker, jm1);
            String tm1s = state(docker, tm1);
            out(p + "after-teardown jobmanager1=" + jm1s + " taskmanager1=" + tm1s);
            check(e, run, "teardown_no_exception", !threw, "no_exception",
                    threw ? thrown.substring(0, Math.min(120, thrown.length())) : "none");
            check(e, run, "teardown_time_bound", tdMs <= TEARDOWN_BOUND_SEC * 1000L,
                    "<=" + TEARDOWN_BOUND_SEC + "s", tdMs + "ms");
            check(e, run, "containers_absent_after_teardown", absent(docker, jm1) && absent(docker, tm1),
                    "jobmanager1=removed,taskmanager1=removed",
                    "jobmanager1=" + jm1s + ",taskmanager1=" + tm1s);
            ReplayFlink18 c2 = new ReplayFlink18();
            String jm2 = null;
            String tm2 = null;
            String job = "not_run";
            String own = "not_measured";
            String leaked = "not_measured";
            try {
                t0 = System.nanoTime();
                c2.startUp();
                jm2 = c2.jm().getContainerId();
                tm2 = c2.tm().getContainerId();
                out(p + "startUp2 ok seconds=" + (System.nanoTime() - t0) / 1_000_000_000L);
                // The TaskManager log names the JobManager only by its alias ("jobmanager"), so
                // count registered TaskManagers through each JobManager's REST API instead.
                boolean jm1Running = state(docker, jm1).contains("running=true");
                own = tmCount(c2.jm());
                leaked = jm1Running ? tmCount(c1.jm()) : "n/a(jobmanager1 not running)";
                out(p + "taskmanager2 registration: taskmanagers_at_own_jm=" + own
                        + " taskmanagers_at_leaked_jm=" + leaked + " jobmanager1=" + state(docker, jm1));
                job = runJob(c2, "/fake_to_assert.conf");
                out(p + "next job " + job);
            } catch (Throwable t) {
                job = "threw " + oneLine(t);
                out(p + "startUp2/next job threw " + oneLine(t));
            } finally {
                check(e, run, "new_taskmanager_at_own_jobmanager", "1".equals(own),
                        "taskmanagers_at_own_jm=1", "own=" + own + ",leaked=" + leaked);
                check(e, run, "next_job_exit_zero", jobExitZero(job), "exit=0",
                        job.length() > 60 ? job.substring(0, 60) : job);
                check(e, run, "next_job_time_bound", jobWithinBound(job), "<=" + JOB_TIMEOUT_SEC + "s",
                        job.startsWith("TIMEOUT") ? "timeout" : "seconds=" + jobSeconds(job));
                try {
                    c2.tearDown();
                } catch (Throwable t) {
                    out(p + "teardown2 threw " + oneLine(t));
                }
                forceRemove(docker, jm1, "jobmanager1");
                forceRemove(docker, tm1, "taskmanager1");
                forceRemove(docker, jm2, "jobmanager2");
                forceRemove(docker, tm2, "taskmanager2");
                boolean clean = absent(docker, jm1) && absent(docker, tm1) && absent(docker, jm2)
                        && absent(docker, tm2);
                java.util.List<String> post = engineContainers(docker, FLINK_IMAGE);
                check(e, run, "post_run_no_leftover_containers", clean && post.isEmpty(), "none",
                        post.toString());
            }
            out(p + "done");
        }
    }

    @Test
    void spark3MasterKilled() throws Exception {
        DockerClient docker = DockerClientFactory.instance().client();
        final String e = "spark3";
        session();
        for (int run = 1; run <= RUNS; run++) {
            String p = "spark3 run=" + run + " ";
            java.util.List<String> pre = engineContainers(docker, SPARK_IMAGE);
            check(e, run, "pre_run_no_engine_containers", pre.isEmpty(), "none", pre.toString());
            if (!pre.isEmpty()) {
                abort(e, run, "containers of " + SPARK_IMAGE + " exist before the run " + pre);
            }
            ReplaySpark3 c1 = new ReplaySpark3();
            long t0 = System.nanoTime();
            c1.startUp();
            out(p + "startUp1 ok seconds=" + (System.nanoTime() - t0) / 1_000_000_000L);
            String m1 = c1.master().getContainerId();
            docker.killContainerCmd(m1).exec();
            out(p + "killed master " + m1.substring(0, 12) + " state=" + state(docker, m1));
            boolean threw = false;
            String thrown = "none";
            t0 = System.nanoTime();
            try {
                c1.tearDown();
                out(p + "teardown completed");
            } catch (Throwable t) {
                threw = true;
                thrown = oneLine(t);
                out(p + "teardown threw " + thrown);
            }
            long tdMs = (System.nanoTime() - t0) / 1_000_000L;
            out(p + "teardown millis=" + tdMs);
            String m1s = state(docker, m1);
            out(p + "after-teardown master1=" + m1s);
            check(e, run, "teardown_no_exception", !threw, "no_exception",
                    threw ? thrown.substring(0, Math.min(120, thrown.length())) : "none");
            check(e, run, "teardown_time_bound", tdMs <= TEARDOWN_BOUND_SEC * 1000L,
                    "<=" + TEARDOWN_BOUND_SEC + "s", tdMs + "ms");
            check(e, run, "containers_absent_after_teardown", absent(docker, m1), "master1=removed",
                    "master1=" + m1s);
            ReplaySpark3 c2 = new ReplaySpark3();
            String m2 = null;
            String job = "not_run";
            try {
                t0 = System.nanoTime();
                c2.startUp();
                m2 = c2.master().getContainerId();
                out(p + "startUp2 ok seconds=" + (System.nanoTime() - t0) / 1_000_000_000L);
                job = runJob(c2, "/fake_to_assert.conf");
                out(p + "next job " + job);
            } catch (Throwable t) {
                job = "threw " + oneLine(t);
                out(p + "startUp2/next job threw " + oneLine(t));
            } finally {
                check(e, run, "next_job_exit_zero", jobExitZero(job), "exit=0",
                        job.length() > 60 ? job.substring(0, 60) : job);
                check(e, run, "next_job_time_bound", jobWithinBound(job), "<=" + JOB_TIMEOUT_SEC + "s",
                        job.startsWith("TIMEOUT") ? "timeout" : "seconds=" + jobSeconds(job));
                try {
                    c2.tearDown();
                } catch (Throwable t) {
                    out(p + "teardown2 threw " + oneLine(t));
                }
                forceRemove(docker, m1, "master1");
                forceRemove(docker, m2, "master2");
                java.util.List<String> post = engineContainers(docker, SPARK_IMAGE);
                check(e, run, "post_run_no_leftover_containers",
                        absent(docker, m1) && absent(docker, m2) && post.isEmpty(), "none",
                        post.toString());
            }
            out(p + "done");
        }
    }
}
