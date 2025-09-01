import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Final

import uvicorn
from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from chatbot2k.config import DATABASE_FILE_ENV_VARIABLE
from chatbot2k.config import get_environment_variable_or_raise
from chatbot2k.core import run_main_loop
from chatbot2k.database.engine import create_database_url
from chatbot2k.database.migrate import upgrade_to_head
from chatbot2k.dependencies import get_app_state
from chatbot2k.routes import commands
from chatbot2k.routes import imprint
from chatbot2k.routes import overlay

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    # Run database migrations.
    upgrade_to_head(
        database_url=create_database_url(Path(get_environment_variable_or_raise(DATABASE_FILE_ENV_VARIABLE)))
    )
    asyncio.create_task(run_main_loop(get_app_state()))
    yield


STATIC_FILES_DIRECTORY = Path(__file__).parent.parent.parent / "static"
if not STATIC_FILES_DIRECTORY.exists():
    raise FileNotFoundError(f"Static files directory {STATIC_FILES_DIRECTORY} does not exist.")

app: Final = FastAPI(lifespan=lifespan)
app.include_router(commands.router)
app.include_router(imprint.router)
app.include_router(overlay.router)
app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)

if __name__ == "__main__":
    uvicorn.run(app)
