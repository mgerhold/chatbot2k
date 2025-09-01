#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] starting..."
export PYTHONUNBUFFERED=1

# Build DATABASE_URL from env if needed:
# Priority: DATABASE_URL > DATABASE_FILE > default path.
if [[ -z "${DATABASE_URL:-}" ]]; then
  if [[ -n "${DATABASE_FILE:-}" ]]; then
    # Resolve to absolute path inside the container
    if [[ "${DATABASE_FILE}" = /* ]]; then
      abs_path="${DATABASE_FILE}"
    else
      abs_path="/app/${DATABASE_FILE}"   # .env uses "storage/database.sqlite"
    fi
  else
    abs_path="/app/storage/database.sqlite"
  fi

  # Make sure the directory exists (important for SQLite)
  db_dir="$(dirname "$abs_path")"
  mkdir -p "$db_dir"

  # For absolute UNIX paths, just use three slashes + the absolute path that starts with /
  # => "sqlite:///" + "/app/..." => "sqlite:////app/..."
  export DATABASE_URL="sqlite:///${abs_path}"

  # Optional debug:
  echo "[entrypoint] DATABASE_URL=${DATABASE_URL}"
  echo "[entrypoint] ls -ld $db_dir && ls -l $db_dir" || true
fi

: "${RUN_MIGRATIONS:=1}"

if [[ "$RUN_MIGRATIONS" = "1" ]]; then
  echo "[entrypoint] checking DB state…"

  NEED_STAMP=$(
    uv run python - <<'PY'
import os, os.path
from sqlalchemy import create_engine, inspect

url = os.environ["DATABASE_URL"]  # guaranteed by the shell logic above
kw = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
engine = create_engine(url, **kw)
insp = inspect(engine)

# "schema exists" heuristic: any user tables present
exists_schema = bool(insp.get_table_names())
exists_alembic = insp.has_table("alembic_version")
print("YES" if (exists_schema and not exists_alembic) else "NO")
PY
  )

  if [[ "$NEED_STAMP" = "YES" ]]; then
    BASELINE_REV="90615bd027fd"   # <-- your baseline revision id
    echo "[entrypoint] existing schema detected without alembic_version; stamping ${BASELINE_REV}…"
    uv run alembic stamp "$BASELINE_REV"
  else
    echo "[entrypoint] no stamping needed."
  fi

  echo "[entrypoint] applying migrations (upgrade head)…"
  uv run alembic upgrade head
fi

echo "[entrypoint] launching app…"
exec uv run uvicorn --host 0.0.0.0 --port 8080 chatbot2k.main:app
