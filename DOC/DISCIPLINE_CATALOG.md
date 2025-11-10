# Discipline Catalog Loader

This project includes a management command to import a professional catalog of behavior levels and violations from a JSON file and expose them in the Admin pages:

- https://127.0.0.1:8443/admin/discipline/behaviorlevel/
- https://127.0.0.1:8443/admin/discipline/incident/

## Source JSON
Default source file:

- DOC/نماذج الغياب/violations_detailed.json

Structure expected:

```
{
  "behavior_levels": [
    {
      "level": "الأولى",
      "description": "...",
      "violations": [
        {"id": "1-1", "category": "...", "description": "...", "actions": ["..."], "sanctions": ["..."]}
      ]
    }
  ]
}
```

## Load the catalog

From the backend directory:

```powershell
cd backend
python manage.py load_discipline_catalog --purge
```

Notes:
- Use `--purge` the first time or when you want to refresh from scratch.
- You can specify a different path using `--file "D:\\sh_school_015\\DOC\\نماذج الغياب\\violations_detailed.json"`.

## After loading
- Open the admin pages and verify:
  - Behavior Levels are created with numeric codes (1..N) and Arabic names from the file.
  - Violations are populated under the correct level with category, description, default actions and sanctions.

## API (optional)
The catalog is also accessible via the existing Discipline API endpoints documented in `DOC/COMMANDS_HUB.md`:
- GET /api/v1/discipline/behavior-levels/
- GET /api/v1/discipline/violations/

## Troubleshooting
- Ensure migrations are applied: `python manage.py migrate`.
- Ensure you are logged in as a staff/superuser to access the admin.
- If the file path includes Arabic characters, always pass it as a Unicode string and ensure your terminal encoding supports UTF-8.


## Auto-load after migrations
When running migrations for the first time in a fresh database, the catalog will auto-load from the default JSON path if the Discipline tables are empty.

- Controlled by environment variable `DISCIPLINE_AUTOLOAD` (default: true). Set to `false` to disable.
- Looks for the file at `<repo_root>/DOC/نماذج الغياب/violations_detailed.json`.
- Safe no-op if the file is missing or data already exists.

## One-click loader (Windows)
You can use the helper script to load or refresh the catalog:

```powershell
# From repo root
scripts\load_discipline_catalog.ps1 -Purge

# Or specify an explicit file path (recommended when paths contain Arabic characters)
scripts\load_discipline_catalog.ps1 -File "D:\\sh_school_015\\DOC\\repo\\violations_detailed.json" -Purge
```

## Notes
- The command is idempotent (upsert). Re-running it will update existing records without duplicates.
- The legacy command `import_violations` is deprecated in favor of `load_discipline_catalog`.

# Discipline Catalog Loader

This project includes a management command to import a professional catalog of behavior levels and violations from a JSON file and expose them in the Admin pages:

- https://127.0.0.1:8443/admin/discipline/behaviorlevel/
- https://127.0.0.1:8443/admin/discipline/incident/

## Source JSON
Default source file:

- DOC/نماذج الغياب/violations_detailed.json

Structure expected:

```
{
  "behavior_levels": [
    {
      "level": "الأولى",
      "description": "...",
      "violations": [
        {"id": "1-1", "category": "...", "description": "...", "actions": ["..."], "sanctions": ["..."]}
      ]
    }
  ]
}
```

## Load the catalog

From the backend directory:

```powershell
cd backend
python manage.py load_discipline_catalog --purge
```

Notes:
- Use `--purge` the first time or when you want to refresh from scratch.
- You can specify a different path using `--file "D:\\sh_school_015\\DOC\\نماذج الغياب\\violations_detailed.json"`.

## After loading
- Open the admin pages and verify:
  - Behavior Levels are created with numeric codes (1..N) and Arabic names from the file.
  - Violations are populated under the correct level with category, description, default actions and sanctions.

## API (optional)
The catalog is also accessible via the existing Discipline API endpoints documented in `DOC/COMMANDS_HUB.md`:
- GET /api/v1/discipline/behavior-levels/
- GET /api/v1/discipline/violations/

## Troubleshooting
- Ensure migrations are applied: `python manage.py migrate`.
- Ensure you are logged in as a staff/superuser to access the admin.
- If the file path includes Arabic characters, always pass it as a Unicode string and ensure your terminal encoding supports UTF-8.


## Auto-load after migrations
When running migrations for the first time in a fresh database, the catalog will auto-load from the default JSON path if the Discipline tables are empty.

- Controlled by environment variable `DISCIPLINE_AUTOLOAD` (default: true). Set to `false` to disable.
- Looks for the file at `<repo_root>/DOC/نماذج الغياب/violations_detailed.json`.
- Safe no-op if the file is missing or data already exists.

## One-click loader (Windows)
You can use the helper script to load or refresh the catalog:

```powershell
# From repo root
scripts\load_discipline_catalog.ps1 -Purge

# Or specify an explicit file path (recommended when paths contain Arabic characters)
scripts\load_discipline_catalog.ps1 -File "D:\\sh_school_015\\DOC\\repo\\violations_detailed.json" -Purge
```

## Quick start (PostgreSQL + full ensure)
Use the ensure command to apply migrations and load the catalog if needed:

```powershell
# From repo root (PowerShell)
scripts\ensure_discipline_data.ps1 -File "D:\\sh_school_015\\DOC\\repo\\violations_detailed.json" -Purge
```

- Requires PostgreSQL connection in `backend/.env` (PG_DB, PG_USER, PG_PASSWORD, PG_HOST, PG_PORT). You can bring up a local DB with `scripts\db_up.ps1`.
- The command prints record counts before/after and exits non‑zero if the catalog stayed empty.

## Frontend verification
After loading, run the integrated dev environment and browse the violations catalog page:

```powershell
scripts\dev_all.ps1
```

Then open the page and try search/filters:
- https://127.0.0.1:8443/discipline/violations
- API examples:
  - https://127.0.0.1:8443/api/v1/discipline/violations/?level=1
  - https://127.0.0.1:8443/api/v1/discipline/violations/?search=تأخر

## Notes
- The command is idempotent (upsert). Re-running it will update existing records without duplicates.
- The legacy command `import_violations` is deprecated in favor of `load_discipline_catalog`.
