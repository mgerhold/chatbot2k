#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] starting..."
export PYTHONUNBUFFERED=1

# Optional: allow disabling in some envs
: "${RUN_MIGRATIONS:=1}"

if [ "$RUN_MIGRATIONS" = "1" ]; then
  echo "[entrypoint] checking DB state..."
  # Decide DB URL (keep this in sync with your app/env.py)
  : "${DATABASE_URL:=sqlite:////app/storage/database.sqlite}"

  # Detect: schema exists but DB not stamped yet → stamp baseline then upgrade
  NEED_STAMP=$(
    uv run python - <<'PY'
import os
from sqlalchemy import create_engine, inspect
url=os.environ.get(f"sqlite:///{DATABASE_FILE}","sqlite:////app/storage/database.sqlite")
kw = {"connect_args":{"check_same_thread": False}} if url.startswith("sqlite") else {}
engine=create_engine(url, **kw)
insp=inspect(engine)
exists_schema = any(insp.get_table_names())
exists_alembic = insp.has_table("alembic_version")
print("YES" if (exists_schema and not exists_alembic) else "NO")
PY
  )

  if [ "$NEED_STAMP" = "YES" ]; then
    # Use your initial/baseline revision id here:
    BASELINE_REV="90615bd027fd"
    echo "[entrypoint] existing schema detected without alembic_version; stamping to ${BASELINE_REV}…"
    uv run alembic stamp "$BASELINE_REV"
  else
    echo "[entrypoint] no stamping needed."
  fi

  echo "[entrypoint] applying migrations (upgrade head)..."
  uv run alembic upgrade head
fi

echo "[entrypoint] launching app..."
exec uv run uvicorn --host 0.0.0.0 --port 8080 chatbot2k.main:app
