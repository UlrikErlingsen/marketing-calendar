# Privacy

Season Signal does not implement telemetry, advertising, user accounts, tracking pixels, scraping, or outbound data uploads. The moments library ships with the app; no calendar data is fetched at runtime.

Your campaigns and lead times are saved to `data/seasonsignal.json` next to the app (or to the folder in `SEASONSIGNAL_DATA_DIR`). That file never leaves your computer unless you copy it.

Inside Signal Hub (`SIGNAL_HUB=1`) Season Signal saves nothing: campaigns and lead times stay in your browser session and are gone when it ends, and no save file is read or written on the server. Exported `.ics` and XLSX files go wherever you put them — importing an `.ics` into Google, Outlook or Apple Calendar shares its contents with that provider.

If someone deploys the app for others, that operator controls infrastructure logs, retention, authentication, backups and network access and must document those practices separately.
