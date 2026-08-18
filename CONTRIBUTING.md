# Contributing

## Development Setup

Follow [INSTALL.md](INSTALL.md) to provision the database and run the backend and game client.

## Checks

Run the repository checks before opening a pull request:

```bash
python3 -m compileall -q backend/app scripts/verify.py
python3 -m unittest discover -s backend/tests
docker compose config --quiet
npm --prefix game run build
```

The live isolation checks require a configured database, working model credentials, and a running backend:

```bash
backend/.venv/bin/python scripts/verify.py
```

This command deletes interaction data for the seeded demo players before running. Do not point it at data that must be retained.

No formatter or linter is configured in this repository. Match the surrounding Python and JavaScript style, keep comments focused on constraints or non-obvious decisions, and update documentation when configuration or behavior changes.

## Pull Requests

- Keep each pull request focused on one change.
- Describe user-visible behavior and verification performed.
- Do not commit `.env` files, credentials, generated bundles, virtual environments, or `node_modules`.
- Add a verification case when changing memory visibility or retrieval scope.
