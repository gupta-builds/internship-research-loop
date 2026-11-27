<!-- synthetic fixture: invented text for tests, not Anant's writing -->
The parser groups log lines by request id. I wrote it after a lab outage took two days to trace.

- Built the importer for CSV exports.
- Added a retry to the exporter.
- Cut the scheduler's startup from 40 seconds to 6.

The lab still runs it on every nightly job.
