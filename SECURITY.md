# Security policy

## Supported version

The latest released version receives security fixes.

## Reporting

Report suspected vulnerabilities privately to the repository owner before public disclosure. Do not include confidential campaign plans in a report.

## Deployment note

The app has no authentication layer and stores campaigns in a local JSON file. A shared or public deployment needs access control, TLS, a private data directory (`SEASONSIGNAL_DATA_DIR`), backups, dependency updates, and isolation appropriate to how sensitive your campaign plans are. All XLSX export cells are sanitised against spreadsheet formula injection.
