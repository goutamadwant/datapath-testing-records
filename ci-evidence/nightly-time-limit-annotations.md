# Nightly runs with job time-limit annotations

Transcribed from GitHub REST API records of apache/seatunnel saved at the retrieval time shown for each record. Values are copied as returned; nothing was added or recomputed. Run pages: `https://github.com/apache/seatunnel/actions/runs/<run id>`.

Runs: 38929296111, 38766089085, 38595233433, 37956696715, 37649502426, 37493133612, 37220159986, 37140101463.

## Run 38929296111

- Source: https://github.com/apache/seatunnel/actions/runs/38929296111
- Retrieved (UTC): 2026-10-25T04:07:02.030Z
- Created 2026-10-16T16:06:24Z, last updated 2026-10-16T20:11:53Z, conclusion `cancelled`, event `schedule`, head `636fc16f68a92dcf2e5edff616ed9942ce6c1781`

Annotations (one representative cancelled job, as returned):

| Level | Message |
| --- | --- |
| failure | The job has exceeded the maximum execution time of 2h30m0s |
| warning | Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@v4, actions/setup-java@v4. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/ |
| failure | The operation was canceled. |
| failure | Run SeaTunnel on spark failed |
| failure | Run SeaTunnel on spark failed |
| failure | SeaTunnel job executed failed |
| failure | Run SeaTunnel on spark failed |
| failure | Run SeaTunnel on spark failed |
| failure | SeaTunnel job executed failed |
| warning | setup-java v4 is deprecated and will no longer receive updates. Please migrate to actions/setup-java@v5. |
| notice | "The ubuntu-latest label will migrate to Ubuntu 26 beginning October 19, 2026. For more information, see https://github.com/actions/runner-images/issues/14748" |

Failed and cancelled jobs:

| Job | Started (UTC) | Completed (UTC) | Conclusion |
| --- | --- | --- | --- |
| Run / all-connectors-it-3 (11, ubuntu-latest) | 2026-10-16T16:32:55Z | 2026-10-16T19:03:16Z | cancelled |
| Run / all-connectors-it-4 (17, ubuntu-latest) | 2026-10-16T16:32:55Z | 2026-10-16T19:03:23Z | cancelled |
| Run / all-connectors-it-4 (11, ubuntu-latest) | 2026-10-16T16:34:31Z | 2026-10-16T19:04:59Z | cancelled |
| Run / all-connectors-it-3 (17, ubuntu-latest) | 2026-10-16T16:39:37Z | 2026-10-16T19:10:07Z | cancelled |
| Run / all-connectors-it-6 (11, ubuntu-latest) | 2026-10-16T16:33:31Z | 2026-10-16T19:03:55Z | cancelled |
| Run / all-connectors-it-6 (17, ubuntu-latest) | 2026-10-16T16:33:48Z | 2026-10-16T17:32:11Z | failure |
| Run / transform-v2-it-part-1 (17, ubuntu-latest) | 2026-10-16T16:37:43Z | 2026-10-16T18:53:04Z | cancelled |
| Run / jdbc-connectors-it-part-1 (17, ubuntu-latest) | 2026-10-16T16:34:12Z | 2026-10-16T19:04:41Z | cancelled |
| Run / all-connectors-it-5 (11, ubuntu-latest) | 2026-10-16T16:34:01Z | 2026-10-16T19:04:22Z | cancelled |
| Run / transform-v2-it-part-1 (11, ubuntu-latest) | 2026-10-16T16:34:12Z | 2026-10-16T18:49:41Z | cancelled |
| Run / all-connectors-it-7 (17, ubuntu-latest) | 2026-10-16T16:40:12Z | 2026-10-16T19:10:37Z | cancelled |
| Run / transform-v2-it-part-2 (11, ubuntu-latest) | 2026-10-16T16:35:21Z | 2026-10-16T19:35:52Z | cancelled |
| Run / all-connectors-it-2 (17, ubuntu-latest) | 2026-10-16T16:34:38Z | 2026-10-16T19:04:59Z | cancelled |
| Run / all-connectors-it-2 (11, ubuntu-latest) | 2026-10-16T16:34:37Z | 2026-10-16T19:04:57Z | cancelled |
| Run / all-connectors-it-5 (17, ubuntu-latest) | 2026-10-16T16:43:46Z | 2026-10-16T19:14:06Z | cancelled |
| Run / all-connectors-it-1 (11, ubuntu-latest) | 2026-10-16T16:38:14Z | 2026-10-16T19:08:35Z | cancelled |
| Run / all-connectors-it-1 (17, ubuntu-latest) | 2026-10-16T16:37:53Z | 2026-10-16T19:08:20Z | cancelled |
| Run / kafka-connector-it (11, ubuntu-latest) | 2026-10-16T16:39:41Z | 2026-10-16T20:10:14Z | cancelled |
| Run / transform-v2-it-part-2 (17, ubuntu-latest) | 2026-10-16T16:37:18Z | 2026-10-16T19:37:50Z | cancelled |
| Run / kafka-connector-it (17, ubuntu-latest) | 2026-10-16T16:39:58Z | 2026-10-16T20:10:34Z | cancelled |
| Run / mysql-cdc-connector-it (17, ubuntu-latest) | 2026-10-16T16:40:32Z | 2026-10-16T18:41:00Z | cancelled |
| Run / connector-redis-it (17, ubuntu-latest) | 2026-10-16T16:41:06Z | 2026-10-16T20:11:28Z | cancelled |
| Run / mysql-cdc-connector-it (11, ubuntu-latest) | 2026-10-16T16:40:26Z | 2026-10-16T18:40:48Z | cancelled |
| Run / rocketmq-connector-it (11, ubuntu-latest) | 2026-10-16T16:42:59Z | 2026-10-16T18:43:22Z | cancelled |
| Run / connector-redis-it (11, ubuntu-latest) | 2026-10-16T16:41:26Z | 2026-10-16T20:11:51Z | cancelled |
| Run / connector-file-local-it (17, ubuntu-latest) | 2026-10-16T16:46:29Z | 2026-10-16T18:46:52Z | cancelled |
| Run / connector-file-local-it (11, ubuntu-latest) | 2026-10-16T16:44:53Z | 2026-10-16T18:45:16Z | cancelled |

## Run 38766089085

- Source: https://github.com/apache/seatunnel/actions/runs/38766089085
- Retrieved (UTC): 2026-10-25T04:07:02.064Z
- Created 2026-10-15T16:05:53Z, last updated 2026-10-15T22:49:49Z, conclusion `cancelled`, event `schedule`, head `6633b0b461c3b038883d04cee1469f15d62d7d73`

Annotations (one representative cancelled job, as returned):

| Level | Message |
| --- | --- |
| failure | The job has exceeded the maximum execution time of 2h30m0s |
| warning | Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@v4, actions/setup-java@v4. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/ |
| failure | The operation was canceled. |
| failure | SeaTunnel job executed failed |
| warning | setup-java v4 is deprecated and will no longer receive updates. Please migrate to actions/setup-java@v5. |
| notice | "The ubuntu-latest label will migrate to Ubuntu 26 beginning October 19, 2026. For more information, see https://github.com/actions/runner-images/issues/14748" |

Failed and cancelled jobs:

| Job | Started (UTC) | Completed (UTC) | Conclusion |
| --- | --- | --- | --- |
| Run / transform-v2-it-part-1 (11, ubuntu-latest) | 2026-10-15T19:14:24Z | 2026-10-15T21:29:43Z | cancelled |
| Run / jdbc-connectors-it-part-1 (11, ubuntu-latest) | 2026-10-15T19:14:59Z | 2026-10-15T21:45:42Z | cancelled |
| Run / jdbc-connectors-it-part-1 (17, ubuntu-latest) | 2026-10-15T19:15:13Z | 2026-10-15T21:46:26Z | cancelled |
| Run / all-connectors-it-2 (11, ubuntu-latest) | 2026-10-15T19:15:49Z | 2026-10-15T21:46:18Z | cancelled |
| Run / all-connectors-it-4 (17, ubuntu-latest) | 2026-10-15T19:16:04Z | 2026-10-15T21:46:33Z | cancelled |
| Run / all-connectors-it-2 (17, ubuntu-latest) | 2026-10-15T19:15:49Z | 2026-10-15T21:46:45Z | cancelled |
| Run / all-connectors-it-4 (11, ubuntu-latest) | 2026-10-15T19:18:45Z | 2026-10-15T21:49:01Z | cancelled |
| Run / all-connectors-it-5 (11, ubuntu-latest) | 2026-10-15T19:16:19Z | 2026-10-15T21:46:40Z | cancelled |
| Run / all-connectors-it-6 (17, ubuntu-latest) | 2026-10-15T19:16:00Z | 2026-10-15T21:46:07Z | cancelled |
| Run / all-connectors-it-3 (11, ubuntu-latest) | 2026-10-15T19:15:54Z | 2026-10-15T21:46:22Z | cancelled |
| Run / all-connectors-it-5 (17, ubuntu-latest) | 2026-10-15T19:16:23Z | 2026-10-15T21:46:45Z | cancelled |
| Run / all-connectors-it-7 (17, ubuntu-latest) | 2026-10-15T19:15:12Z | 2026-10-15T21:45:41Z | cancelled |
| Run / all-connectors-it-3 (17, ubuntu-latest) | 2026-10-15T19:15:54Z | 2026-10-15T21:46:15Z | cancelled |
| Run / amazonSqs-connector-it (17, ubuntu-latest) | 2026-10-15T19:15:59Z | 2026-10-15T21:16:22Z | cancelled |
| Run / all-connectors-it-7 (11, ubuntu-latest) | 2026-10-15T19:23:22Z | 2026-10-15T21:54:49Z | cancelled |
| Run / kafka-connector-it (17, ubuntu-latest) | 2026-10-15T19:18:20Z | 2026-10-15T22:49:09Z | cancelled |
| Run / mysql-cdc-connector-it (17, ubuntu-latest) | 2026-10-15T19:18:03Z | 2026-10-15T21:18:23Z | cancelled |
| Run / connector-redis-it (17, ubuntu-latest) | 2026-10-15T19:19:17Z | 2026-10-15T22:49:48Z | cancelled |
| Run / kafka-connector-it (11, ubuntu-latest) | 2026-10-15T19:18:20Z | 2026-10-15T22:49:20Z | cancelled |
| Run / mysql-cdc-connector-it (11, ubuntu-latest) | 2026-10-15T19:18:20Z | 2026-10-15T21:18:42Z | cancelled |
| Run / connector-file-local-it (11, ubuntu-latest) | 2026-10-15T19:22:46Z | 2026-10-15T21:23:40Z | cancelled |
| Run / connector-file-local-it (17, ubuntu-latest) | 2026-10-15T19:23:20Z | 2026-10-15T21:24:37Z | cancelled |

## Run 38595233433

- Source: https://github.com/apache/seatunnel/actions/runs/38595233433
- Retrieved (UTC): 2026-10-25T04:07:02.098Z
- Created 2026-10-14T16:06:35Z, last updated 2026-10-14T23:32:36Z, conclusion `cancelled`, event `schedule`, head `42d2aab3f841821753b415d568cc5884d6f13bbd`

Annotations (one representative cancelled job, as returned):

| Level | Message |
| --- | --- |
| failure | The job has exceeded the maximum execution time of 2h30m0s |
| warning | Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@v4, actions/setup-java@v4. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/ |
| failure | The operation was canceled. |
| failure | Run SeaTunnel on spark failed |
| failure | Run SeaTunnel on spark failed |
| failure | SeaTunnel job executed failed |
| failure | Run SeaTunnel on spark failed |
| failure | Run SeaTunnel on spark failed |
| failure | SeaTunnel job executed failed |
| warning | setup-java v4 is deprecated and will no longer receive updates. Please migrate to actions/setup-java@v5. |
| notice | "The ubuntu-latest label will migrate to Ubuntu 26 beginning October 19, 2026. For more information, see https://github.com/actions/runner-images/issues/14748" |

Failed and cancelled jobs:

| Job | Started (UTC) | Completed (UTC) | Conclusion |
| --- | --- | --- | --- |
| Run / all-connectors-it-3 (11, ubuntu-latest) | 2026-10-14T19:19:54Z | 2026-10-14T21:50:22Z | cancelled |
| Run / all-connectors-it-3 (17, ubuntu-latest) | 2026-10-14T19:19:54Z | 2026-10-14T21:50:29Z | cancelled |
| Run / all-connectors-it-5 (17, ubuntu-latest) | 2026-10-14T19:21:07Z | 2026-10-14T21:51:37Z | cancelled |
| Run / all-connectors-it-4 (17, ubuntu-latest) | 2026-10-14T19:56:47Z | 2026-10-14T22:27:08Z | cancelled |
| Run / all-connectors-it-5 (11, ubuntu-latest) | 2026-10-14T19:25:34Z | 2026-10-14T21:56:09Z | cancelled |
| Run / all-connectors-it-7 (17, ubuntu-latest) | 2026-10-14T19:20:59Z | 2026-10-14T21:51:21Z | cancelled |
| Run / all-connectors-it-2 (11, ubuntu-latest) | 2026-10-14T19:32:59Z | 2026-10-14T22:03:32Z | cancelled |
| Run / all-connectors-it-7 (11, ubuntu-latest) | 2026-10-14T19:40:26Z | 2026-10-14T22:10:48Z | cancelled |
| Run / all-connectors-it-1 (11, ubuntu-latest) | 2026-10-14T19:21:07Z | 2026-10-14T21:51:34Z | cancelled |
| Run / all-connectors-it-1 (17, ubuntu-latest) | 2026-10-14T19:21:07Z | 2026-10-14T21:51:34Z | cancelled |
| Run / mysql-cdc-connector-it (11, ubuntu-latest) | 2026-10-14T19:21:19Z | 2026-10-14T21:21:51Z | cancelled |
| Run / connector-file-local-it (17, ubuntu-latest) | 2026-10-14T19:55:22Z | 2026-10-14T21:55:46Z | cancelled |
| Run / mysql-cdc-connector-it (17, ubuntu-latest) | 2026-10-14T19:21:40Z | 2026-10-14T21:22:11Z | cancelled |
| Run / jdbc-connectors-it-part-1 (11, ubuntu-latest) | 2026-10-14T19:44:38Z | 2026-10-14T22:15:08Z | cancelled |
| Run / kafka-connector-it (11, ubuntu-latest) | 2026-10-14T19:41:22Z | 2026-10-14T23:12:02Z | cancelled |
| Run / connector-file-local-it (11, ubuntu-latest) | 2026-10-14T19:56:05Z | 2026-10-14T21:56:43Z | cancelled |
| Run / connector-redis-it (11, ubuntu-latest) | 2026-10-14T19:20:54Z | 2026-10-14T22:51:23Z | cancelled |
| Run / kafka-connector-it (17, ubuntu-latest) | 2026-10-14T20:02:11Z | 2026-10-14T23:32:35Z | cancelled |

## Run 37956696715

- Source: https://github.com/apache/seatunnel/actions/runs/37956696715
- Retrieved (UTC): 2026-10-25T04:07:02.142Z
- Created 2026-10-09T16:06:36Z, last updated 2026-10-09T21:15:55Z, conclusion `cancelled`, event `schedule`, head `0278a6a74746856488dd27713736f008e3115c11`

Annotations (one representative cancelled job, as returned):

| Level | Message |
| --- | --- |
| failure | The job has exceeded the maximum execution time of 2h30m0s |
| warning | Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@v4, actions/setup-java@v4. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/ |
| failure | The operation was canceled. |
| failure | SeaTunnel job executed failed |
| failure | SeaTunnel job executed failed |
| warning | setup-java v4 is deprecated and will no longer receive updates. Please migrate to actions/setup-java@v5. |
| notice | "The ubuntu-latest label will migrate to Ubuntu 26 beginning October 19, 2026. For more information, see https://github.com/actions/runner-images/issues/14748" |

Failed and cancelled jobs:

| Job | Started (UTC) | Completed (UTC) | Conclusion |
| --- | --- | --- | --- |
| Run / all-connectors-it-5 (11, ubuntu-latest) | 2026-10-09T17:36:10Z | 2026-10-09T20:06:40Z | cancelled |
| Run / kafka-connector-it (17, ubuntu-latest) | 2026-10-09T17:23:49Z | 2026-10-09T20:54:20Z | cancelled |
| Run / all-connectors-it-5 (17, ubuntu-latest) | 2026-10-09T17:23:49Z | 2026-10-09T19:54:13Z | cancelled |
| Run / transform-v2-it-part-2 (11, ubuntu-latest) | 2026-10-09T17:29:12Z | 2026-10-09T20:29:38Z | cancelled |
| Run / all-connectors-it-2 (11, ubuntu-latest) | 2026-10-09T17:41:33Z | 2026-10-09T20:11:52Z | cancelled |
| Run / connector-file-local-it (17, ubuntu-latest) | 2026-10-09T17:31:02Z | 2026-10-09T19:31:24Z | cancelled |
| Run / mysql-cdc-connector-it (17, ubuntu-latest) | 2026-10-09T17:43:55Z | 2026-10-09T19:44:23Z | cancelled |
| Run / kafka-connector-it (11, ubuntu-latest) | 2026-10-09T17:24:25Z | 2026-10-09T20:54:58Z | cancelled |
| Run / all-connectors-it-1 (11, ubuntu-latest) | 2026-10-09T17:25:38Z | 2026-10-09T19:55:57Z | cancelled |
| Run / connector-file-local-it (11, ubuntu-latest) | 2026-10-09T17:31:15Z | 2026-10-09T19:31:37Z | cancelled |
| Run / elasticsearch-connector-it (17, ubuntu-latest) | 2026-10-09T17:40:47Z | 2026-10-09T20:10:54Z | failure |
| Run / jdbc-connectors-it-part-1 (11, ubuntu-latest) | 2026-10-09T17:37:36Z | 2026-10-09T20:08:06Z | cancelled |
| Run / elasticsearch-connector-it (11, ubuntu-latest) | 2026-10-09T17:40:49Z | 2026-10-09T20:13:21Z | failure |
| Run / all-connectors-it-3 (11, ubuntu-latest) | 2026-10-09T17:36:22Z | 2026-10-09T20:06:41Z | cancelled |
| Run / jdbc-connectors-it-part-1 (17, ubuntu-latest) | 2026-10-09T17:38:31Z | 2026-10-09T20:08:52Z | cancelled |
| Run / mysql-cdc-connector-it (11, ubuntu-latest) | 2026-10-09T17:43:55Z | 2026-10-09T19:44:14Z | cancelled |
| Run / transform-v2-it-part-1 (17, ubuntu-latest) | 2026-10-09T17:42:52Z | 2026-10-09T19:58:14Z | cancelled |
| Run / all-connectors-it-3 (17, ubuntu-latest) | 2026-10-09T17:37:03Z | 2026-10-09T20:07:28Z | cancelled |
| Run / all-connectors-it-4 (17, ubuntu-latest) | 2026-10-09T17:36:10Z | 2026-10-09T20:06:39Z | cancelled |
| Run / transform-v2-it-part-1 (11, ubuntu-latest) | 2026-10-09T17:28:09Z | 2026-10-09T19:43:31Z | cancelled |
| Run / all-connectors-it-2 (17, ubuntu-latest) | 2026-10-09T17:41:11Z | 2026-10-09T20:11:34Z | cancelled |
| Run / connector-redis-it (17, ubuntu-latest) | 2026-10-09T17:42:13Z | 2026-10-09T21:12:46Z | cancelled |
| Run / all-connectors-it-7 (17, ubuntu-latest) | 2026-10-09T17:43:57Z | 2026-10-09T20:14:25Z | cancelled |
| Run / all-connectors-it-7 (11, ubuntu-latest) | 2026-10-09T17:45:28Z | 2026-10-09T20:15:53Z | cancelled |
| Run / connector-redis-it (11, ubuntu-latest) | 2026-10-09T17:45:32Z | 2026-10-09T21:15:54Z | cancelled |
| Run / all-connectors-it-4 (11, ubuntu-latest) | 2026-10-09T17:45:29Z | 2026-10-09T20:15:59Z | cancelled |

## Run 37649502426

- Source: https://github.com/apache/seatunnel/actions/runs/37649502426
- Retrieved (UTC): 2026-10-25T04:07:02.184Z
- Created 2026-10-07T16:07:00Z, last updated 2026-10-07T20:12:27Z, conclusion `cancelled`, event `schedule`, head `3ac7003fb90d35e5945f94834742247fabd3dec7`

Annotations (one representative cancelled job, as returned):

| Level | Message |
| --- | --- |
| failure | The job has exceeded the maximum execution time of 2h30m0s |
| warning | Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@v4, actions/setup-java@v4. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/ |
| failure | The operation was canceled. |
| warning | setup-java v4 is deprecated and will no longer receive updates. Please migrate to actions/setup-java@v5. |
| notice | "The ubuntu-latest label will migrate to Ubuntu 26 beginning October 19, 2026. For more information, see https://github.com/actions/runner-images/issues/14748" |

Failed and cancelled jobs:

| Job | Started (UTC) | Completed (UTC) | Conclusion |
| --- | --- | --- | --- |
| Run / all-connectors-it-7 (8, ubuntu-latest) | 2026-10-07T16:36:59Z | 2026-10-07T19:07:31Z | cancelled |
| Run / all-connectors-it-1 (8, ubuntu-latest) | 2026-10-07T16:37:18Z | 2026-10-07T19:08:20Z | cancelled |
| Run / jdbc-connectors-it-part-1 (8, ubuntu-latest) | 2026-10-07T16:36:12Z | 2026-10-07T19:06:33Z | cancelled |
| Run / all-connectors-it-1 (11, ubuntu-latest) | 2026-10-07T16:36:54Z | 2026-10-07T19:07:19Z | cancelled |
| Run / all-connectors-it-3 (8, ubuntu-latest) | 2026-10-07T16:37:11Z | 2026-10-07T19:07:35Z | cancelled |
| Run / transform-v2-it-part-2 (8, ubuntu-latest) | 2026-10-07T16:37:00Z | 2026-10-07T19:37:34Z | cancelled |
| Run / all-connectors-it-3 (11, ubuntu-latest) | 2026-10-07T16:37:12Z | 2026-10-07T19:07:44Z | cancelled |
| Run / all-connectors-it-5 (11, ubuntu-latest) | 2026-10-07T16:36:59Z | 2026-10-07T19:07:27Z | cancelled |
| Run / all-connectors-it-2 (8, ubuntu-latest) | 2026-10-07T16:36:44Z | 2026-10-07T19:07:16Z | cancelled |
| Run / jdbc-connectors-it-part-1 (11, ubuntu-latest) | 2026-10-07T16:39:15Z | 2026-10-07T19:09:48Z | cancelled |
| Run / transform-v2-it-part-1 (11, ubuntu-latest) | 2026-10-07T16:36:53Z | 2026-10-07T18:52:18Z | cancelled |
| Run / all-connectors-it-4 (8, ubuntu-latest) | 2026-10-07T16:37:53Z | 2026-10-07T19:08:20Z | cancelled |
| Run / all-connectors-it-5 (8, ubuntu-latest) | 2026-10-07T16:36:58Z | 2026-10-07T19:07:22Z | cancelled |
| Run / all-connectors-it-4 (11, ubuntu-latest) | 2026-10-07T16:37:53Z | 2026-10-07T19:08:25Z | cancelled |
| Run / kafka-connector-it (8, ubuntu-latest) | 2026-10-07T16:41:22Z | 2026-10-07T20:12:24Z | cancelled |
| Run / elasticsearch-connector-it (11, ubuntu-latest) | 2026-10-07T16:42:04Z | 2026-10-07T19:42:31Z | cancelled |
| Run / elasticsearch-connector-it (8, ubuntu-latest) | 2026-10-07T16:39:30Z | 2026-10-07T19:40:04Z | cancelled |
| Run / connector-redis-it (8, ubuntu-latest) | 2026-10-07T16:40:50Z | 2026-10-07T20:11:30Z | cancelled |
| Run / mysql-cdc-connector-it (11, ubuntu-latest) | 2026-10-07T16:38:46Z | 2026-10-07T18:39:13Z | cancelled |
| Run / connector-file-local-it (8, ubuntu-latest) | 2026-10-07T16:42:41Z | 2026-10-07T18:43:04Z | cancelled |
| Run / mysql-cdc-connector-it (8, ubuntu-latest) | 2026-10-07T16:43:54Z | 2026-10-07T18:44:20Z | cancelled |
| Run / connector-file-local-it (11, ubuntu-latest) | 2026-10-07T16:41:33Z | 2026-10-07T18:41:53Z | cancelled |
| Run / rocketmq-connector-it (8, ubuntu-latest) | 2026-10-07T16:44:54Z | 2026-10-07T18:45:16Z | cancelled |
| Run / transform-v2-it-part-2 (11, ubuntu-latest) | 2026-10-07T16:45:36Z | 2026-10-07T19:46:07Z | cancelled |
| Run / kafka-connector-it (11, ubuntu-latest) | 2026-10-07T16:41:46Z | 2026-10-07T20:12:26Z | cancelled |

## Run 37493133612

- Source: https://github.com/apache/seatunnel/actions/runs/37493133612
- Retrieved (UTC): 2026-10-25T04:07:02.226Z
- Created 2026-10-06T16:07:02Z, last updated 2026-10-06T19:48:22Z, conclusion `cancelled`, event `schedule`, head `11e4f5554973a66ba2d63d4df18ee22f10be121f`

Annotations (one representative cancelled job, as returned):

| Level | Message |
| --- | --- |
| failure | The job has exceeded the maximum execution time of 2h30m0s |
| warning | Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@v4, actions/setup-java@v4. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/ |
| failure | The operation was canceled. |
| warning | setup-java v4 is deprecated and will no longer receive updates. Please migrate to actions/setup-java@v5. |
| notice | "The ubuntu-latest label will migrate to Ubuntu 26 beginning October 19, 2026. For more information, see https://github.com/actions/runner-images/issues/14748" |

Failed and cancelled jobs:

| Job | Started (UTC) | Completed (UTC) | Conclusion |
| --- | --- | --- | --- |
| Run / Dead links | 2026-10-06T16:13:30Z | 2026-10-06T16:22:00Z | failure |
| Run / transform-v2-it-part-2 (11, ubuntu-latest) | 2026-10-06T16:15:59Z | 2026-10-06T19:16:28Z | cancelled |
| Run / transform-v2-it-part-2 (8, ubuntu-latest) | 2026-10-06T16:16:07Z | 2026-10-06T19:16:32Z | cancelled |
| Run / all-connectors-it-2 (8, ubuntu-latest) | 2026-10-06T16:16:06Z | 2026-10-06T18:46:39Z | cancelled |
| Run / all-connectors-it-4 (8, ubuntu-latest) | 2026-10-06T16:16:07Z | 2026-10-06T18:46:30Z | cancelled |
| Run / all-connectors-it-1 (8, ubuntu-latest) | 2026-10-06T16:16:12Z | 2026-10-06T18:47:14Z | cancelled |
| Run / all-connectors-it-5 (8, ubuntu-latest) | 2026-10-06T16:16:10Z | 2026-10-06T18:46:31Z | cancelled |
| Run / all-connectors-it-4 (11, ubuntu-latest) | 2026-10-06T16:16:27Z | 2026-10-06T18:46:49Z | cancelled |
| Run / transform-v2-it-part-1 (8, ubuntu-latest) | 2026-10-06T16:16:18Z | 2026-10-06T18:33:00Z | cancelled |
| Run / all-connectors-it-3 (11, ubuntu-latest) | 2026-10-06T16:16:31Z | 2026-10-06T18:46:59Z | cancelled |
| Run / all-connectors-it-3 (8, ubuntu-latest) | 2026-10-06T16:16:34Z | 2026-10-06T18:47:05Z | cancelled |
| Run / transform-v2-it-part-1 (11, ubuntu-latest) | 2026-10-06T16:16:15Z | 2026-10-06T18:31:39Z | cancelled |
| Run / all-connectors-it-5 (11, ubuntu-latest) | 2026-10-06T16:16:16Z | 2026-10-06T18:46:40Z | cancelled |
| Run / elasticsearch-connector-it (11, ubuntu-latest) | 2026-10-06T16:17:50Z | 2026-10-06T19:18:47Z | cancelled |
| Run / connector-file-local-it (8, ubuntu-latest) | 2026-10-06T16:16:24Z | 2026-10-06T18:17:35Z | cancelled |
| Run / connector-redis-it (11, ubuntu-latest) | 2026-10-06T16:17:08Z | 2026-10-06T19:47:37Z | cancelled |
| Run / mysql-cdc-connector-it (8, ubuntu-latest) | 2026-10-06T16:16:18Z | 2026-10-06T18:16:41Z | cancelled |
| Run / elasticsearch-connector-it (8, ubuntu-latest) | 2026-10-06T16:17:46Z | 2026-10-06T19:18:13Z | cancelled |
| Run / connector-redis-it (8, ubuntu-latest) | 2026-10-06T16:17:03Z | 2026-10-06T19:47:31Z | cancelled |
| Run / connector-file-local-it (11, ubuntu-latest) | 2026-10-06T16:16:26Z | 2026-10-06T18:16:45Z | cancelled |
| Run / jdbc-connectors-it-part-1 (11, ubuntu-latest) | 2026-10-06T16:17:45Z | 2026-10-06T18:48:05Z | cancelled |
| Run / jdbc-connectors-it-part-1 (8, ubuntu-latest) | 2026-10-06T16:17:46Z | 2026-10-06T18:48:17Z | cancelled |
| Run / mysql-cdc-connector-it (11, ubuntu-latest) | 2026-10-06T16:16:22Z | 2026-10-06T18:17:22Z | cancelled |
| Run / kafka-connector-it (11, ubuntu-latest) | 2026-10-06T16:17:52Z | 2026-10-06T19:48:15Z | cancelled |
| Run / all-connectors-it-7 (8, ubuntu-latest) | 2026-10-06T16:18:05Z | 2026-10-06T18:48:37Z | cancelled |
| Run / kafka-connector-it (8, ubuntu-latest) | 2026-10-06T16:17:54Z | 2026-10-06T19:48:21Z | cancelled |

## Run 37220159986

- Source: https://github.com/apache/seatunnel/actions/runs/37220159986
- Retrieved (UTC): 2026-10-25T04:07:02.264Z
- Created 2026-10-04T17:20:51Z, last updated 2026-10-04T20:54:46Z, conclusion `cancelled`, event `schedule`, head `af80a6704be4734b20a913f46f3838c3770688eb`

Annotations (one representative cancelled job, as returned):

| Level | Message |
| --- | --- |
| failure | The job has exceeded the maximum execution time of 2h30m0s |
| warning | Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@v4, actions/setup-java@v4. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/ |
| failure | The operation was canceled. |
| warning | setup-java v4 is deprecated and will no longer receive updates. Please migrate to actions/setup-java@v5. |
| notice | "The ubuntu-latest label will migrate to Ubuntu 26 beginning October 19, 2026. For more information, see https://github.com/actions/runner-images/issues/14748" |

Failed and cancelled jobs:

| Job | Started (UTC) | Completed (UTC) | Conclusion |
| --- | --- | --- | --- |
| Run / Dead links | 2026-10-04T17:20:54Z | 2026-10-04T17:28:47Z | failure |
| Run / Build website | 2026-10-04T17:24:18Z | 2026-10-04T18:54:36Z | cancelled |
| Run / all-connectors-it-2 (11, ubuntu-latest) | 2026-10-04T17:24:18Z | 2026-10-04T19:54:44Z | cancelled |
| Run / all-connectors-it-1 (8, ubuntu-latest) | 2026-10-04T17:24:18Z | 2026-10-04T19:54:35Z | cancelled |
| Run / jdbc-connectors-it-part-1 (8, ubuntu-latest) | 2026-10-04T17:24:18Z | 2026-10-04T19:54:34Z | cancelled |
| Run / jdbc-connectors-it-part-1 (11, ubuntu-latest) | 2026-10-04T17:24:19Z | 2026-10-04T19:54:45Z | cancelled |
| Run / engine-v2-it (8, ubuntu-latest) | 2026-10-04T17:24:18Z | 2026-10-04T19:21:59Z | failure |
| Run / all-connectors-it-4 (8, ubuntu-latest) | 2026-10-04T17:24:19Z | 2026-10-04T19:54:38Z | cancelled |
| Run / all-connectors-it-3 (11, ubuntu-latest) | 2026-10-04T17:24:19Z | 2026-10-04T19:54:35Z | cancelled |
| Run / all-connectors-it-7 (11, ubuntu-latest) | 2026-10-04T17:24:19Z | 2026-10-04T19:54:44Z | cancelled |
| Run / transform-v2-it-part-1 (8, ubuntu-latest) | 2026-10-04T17:24:18Z | 2026-10-04T19:39:37Z | cancelled |
| Run / all-connectors-it-2 (8, ubuntu-latest) | 2026-10-04T17:24:18Z | 2026-10-04T19:54:38Z | cancelled |
| Run / transform-v2-it-part-2 (11, ubuntu-latest) | 2026-10-04T17:24:20Z | 2026-10-04T20:24:43Z | cancelled |
| Run / all-connectors-it-4 (11, ubuntu-latest) | 2026-10-04T17:24:18Z | 2026-10-04T19:54:40Z | cancelled |
| Run / transform-v2-it-part-2 (8, ubuntu-latest) | 2026-10-04T17:24:20Z | 2026-10-04T20:24:37Z | cancelled |
| Run / kafka-connector-it (8, ubuntu-latest) | 2026-10-04T17:24:18Z | 2026-10-04T20:54:40Z | cancelled |
| Run / kafka-connector-it (11, ubuntu-latest) | 2026-10-04T17:24:19Z | 2026-10-04T20:54:45Z | cancelled |
| Run / all-connectors-it-3 (8, ubuntu-latest) | 2026-10-04T17:24:19Z | 2026-10-04T19:54:45Z | cancelled |
| Run / transform-v2-it-part-1 (11, ubuntu-latest) | 2026-10-04T17:24:18Z | 2026-10-04T19:39:37Z | cancelled |
| Run / connector-file-local-it (11, ubuntu-latest) | 2026-10-04T17:24:19Z | 2026-10-04T19:24:41Z | cancelled |
| Run / connector-file-local-it (8, ubuntu-latest) | 2026-10-04T17:24:19Z | 2026-10-04T19:24:45Z | cancelled |
| Run / all-connectors-it-5 (8, ubuntu-latest) | 2026-10-04T17:24:19Z | 2026-10-04T19:54:44Z | cancelled |
| Run / mysql-cdc-connector-it (8, ubuntu-latest) | 2026-10-04T17:24:18Z | 2026-10-04T19:24:40Z | cancelled |
| Run / elasticsearch-connector-it (8, ubuntu-latest) | 2026-10-04T17:24:19Z | 2026-10-04T20:24:43Z | cancelled |
| Run / mysql-cdc-connector-it (11, ubuntu-latest) | 2026-10-04T17:24:18Z | 2026-10-04T19:24:37Z | cancelled |
| Run / connector-redis-it (8, ubuntu-latest) | 2026-10-04T17:24:18Z | 2026-10-04T20:54:34Z | cancelled |

## Run 37140101463

- Source: https://github.com/apache/seatunnel/actions/runs/37140101463
- Retrieved (UTC): 2026-10-25T04:07:02.300Z
- Created 2026-10-03T17:19:44Z, last updated 2026-10-03T20:53:20Z, conclusion `cancelled`, event `schedule`, head `309b15effe99423f73b6007cbe61b97bb6af7b24`

Annotations (one representative cancelled job, as returned):

| Level | Message |
| --- | --- |
| failure | The job has exceeded the maximum execution time of 2h30m0s |
| warning | Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@v4, actions/setup-java@v4. For more information see: https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/ |
| failure | The operation was canceled. |
| warning | setup-java v4 is deprecated and will no longer receive updates. Please migrate to actions/setup-java@v5. |
| notice | "The ubuntu-latest label will migrate to Ubuntu 26 beginning October 19, 2026. For more information, see https://github.com/actions/runner-images/issues/14748" |

Failed and cancelled jobs:

| Job | Started (UTC) | Completed (UTC) | Conclusion |
| --- | --- | --- | --- |
| Run / Dead links | 2026-10-03T17:19:47Z | 2026-10-03T17:27:18Z | failure |
| Run / Build website | 2026-10-03T17:22:44Z | 2026-10-03T18:53:02Z | cancelled |
| Run / transform-v2-it-part-1 (8, ubuntu-latest) | 2026-10-03T17:22:44Z | 2026-10-03T19:38:04Z | cancelled |
| Run / all-connectors-it-2 (8, ubuntu-latest) | 2026-10-03T17:22:44Z | 2026-10-03T19:53:04Z | cancelled |
| Run / all-connectors-it-3 (11, ubuntu-latest) | 2026-10-03T17:22:44Z | 2026-10-03T19:53:11Z | cancelled |
| Run / all-connectors-it-3 (8, ubuntu-latest) | 2026-10-03T17:22:44Z | 2026-10-03T19:53:11Z | cancelled |
| Run / all-connectors-it-2 (11, ubuntu-latest) | 2026-10-03T17:22:44Z | 2026-10-03T19:53:04Z | cancelled |
| Run / all-connectors-it-1 (11, ubuntu-latest) | 2026-10-03T17:22:44Z | 2026-10-03T19:53:14Z | cancelled |
| Run / all-connectors-it-5 (11, ubuntu-latest) | 2026-10-03T17:22:44Z | 2026-10-03T19:53:06Z | cancelled |
| Run / all-connectors-it-7 (11, ubuntu-latest) | 2026-10-03T17:22:44Z | 2026-10-03T19:53:07Z | cancelled |
| Run / all-connectors-it-5 (8, ubuntu-latest) | 2026-10-03T17:22:44Z | 2026-10-03T19:53:05Z | cancelled |
| Run / all-connectors-it-1 (8, ubuntu-latest) | 2026-10-03T17:22:44Z | 2026-10-03T19:53:01Z | cancelled |
| Run / all-connectors-it-4 (11, ubuntu-latest) | 2026-10-03T17:22:44Z | 2026-10-03T19:53:10Z | cancelled |
| Run / jdbc-connectors-it-part-1 (11, ubuntu-latest) | 2026-10-03T17:22:44Z | 2026-10-03T19:52:59Z | cancelled |
| Run / all-connectors-it-4 (8, ubuntu-latest) | 2026-10-03T17:22:44Z | 2026-10-03T19:53:11Z | cancelled |
| Run / all-connectors-it-7 (8, ubuntu-latest) | 2026-10-03T17:22:44Z | 2026-10-03T19:53:12Z | cancelled |
| Run / jdbc-connectors-it-part-1 (8, ubuntu-latest) | 2026-10-03T17:22:44Z | 2026-10-03T19:53:00Z | cancelled |
| Run / engine-v2-it (8, ubuntu-latest) | 2026-10-03T17:22:44Z | 2026-10-03T19:16:00Z | failure |
| Run / kafka-connector-it (8, ubuntu-latest) | 2026-10-03T17:22:46Z | 2026-10-03T20:53:08Z | cancelled |
| Run / kafka-connector-it (11, ubuntu-latest) | 2026-10-03T17:22:44Z | 2026-10-03T20:53:18Z | cancelled |
| Run / mysql-cdc-connector-it (8, ubuntu-latest) | 2026-10-03T17:22:44Z | 2026-10-03T19:23:12Z | cancelled |
| Run / connector-redis-it (8, ubuntu-latest) | 2026-10-03T17:22:44Z | 2026-10-03T20:53:01Z | cancelled |
| Run / connector-file-local-it (11, ubuntu-latest) | 2026-10-03T17:22:44Z | 2026-10-03T19:22:59Z | cancelled |
| Run / connector-redis-it (11, ubuntu-latest) | 2026-10-03T17:22:45Z | 2026-10-03T20:53:20Z | cancelled |
| Run / mysql-cdc-connector-it (11, ubuntu-latest) | 2026-10-03T17:22:44Z | 2026-10-03T19:23:05Z | cancelled |
| Run / rocketmq-connector-it (8, ubuntu-latest) | 2026-10-03T17:22:44Z | 2026-10-03T19:23:03Z | cancelled |
| Run / connector-file-local-it (8, ubuntu-latest) | 2026-10-03T17:22:44Z | 2026-10-03T19:23:00Z | cancelled |

