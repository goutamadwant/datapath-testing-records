/*
 * Part B runner (reconstruction, 2026-10-25). Runs one JUnit 5 test method N times in one JVM
 * through the JUnit Platform launcher, as described in apache/seatunnel PR 12472 ("Each run
 * executed the single method repeatedly in one JVM through the JUnit Platform launcher").
 * Prints one line per iteration: ITER <i> <PASS|FAIL> <millis> <first line of the failure>.
 * usage: java RepeatMethod <fully.qualified.Class> <method> <iterations>
 */
import org.junit.platform.launcher.Launcher;
import org.junit.platform.launcher.LauncherDiscoveryRequest;
import org.junit.platform.launcher.core.LauncherFactory;
import org.junit.platform.launcher.listeners.SummaryGeneratingListener;
import org.junit.platform.launcher.listeners.TestExecutionSummary;

import static org.junit.platform.engine.discovery.DiscoverySelectors.selectMethod;
import static org.junit.platform.launcher.core.LauncherDiscoveryRequestBuilder.request;

public class RepeatMethod {
    public static void main(String[] args) {
        String cls = args[0];
        String method = args[1];
        int n = Integer.parseInt(args[2]);
        Launcher launcher = LauncherFactory.create();
        int failed = 0;
        System.out.println("JVM " + System.getProperty("java.version") + " "
                + System.getProperty("java.vm.name") + " " + System.getProperty("os.arch"));
        for (int i = 1; i <= n; i++) {
            LauncherDiscoveryRequest req = request().selectors(selectMethod(cls + "#" + method)).build();
            SummaryGeneratingListener l = new SummaryGeneratingListener();
            long t0 = System.nanoTime();
            launcher.execute(req, l);
            long ms = (System.nanoTime() - t0) / 1_000_000L;
            TestExecutionSummary s = l.getSummary();
            if (s.getTestsFoundCount() != 1) {
                System.out.println("ITER " + i + " ERROR " + ms + " tests_found=" + s.getTestsFoundCount());
                failed++;
                continue;
            }
            if (s.getTotalFailureCount() == 0 && s.getTestsSucceededCount() == 1) {
                System.out.println("ITER " + i + " PASS " + ms);
            } else {
                failed++;
                StringBuilder msg = new StringBuilder();
                for (TestExecutionSummary.Failure f : s.getFailures()) {
                    Throwable t = f.getException();
                    msg.append(t.getClass().getSimpleName()).append(": ")
                            .append(String.valueOf(t.getMessage()).replace('\n', ' '));
                    Throwable c = t.getCause();
                    while (c != null) {
                        msg.append(" | cause ").append(c.getClass().getSimpleName()).append(": ")
                                .append(String.valueOf(c.getMessage()).replace('\n', ' '));
                        c = c.getCause();
                    }
                }
                System.out.println("ITER " + i + " FAIL " + ms + " " + msg);
            }
        }
        System.out.println("SUMMARY failed=" + failed + "/" + n);
    }
}
