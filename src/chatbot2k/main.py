import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from contextlib import suppress
from pathlib import Path
from typing import Final

import uvicorn
from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from chatbot2k.core import run_main_loop
from chatbot2k.dependencies import get_app_state
from chatbot2k.live_notifications import StreamLiveEvent
from chatbot2k.live_notifications import monitor_streams
from chatbot2k.routes import auth
from chatbot2k.routes import commands
from chatbot2k.routes import imprint
from chatbot2k.routes import login
from chatbot2k.routes import overlay

logging.basicConfig(level=logging.INFO)


logger: Final = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    app_state: Final = get_app_state()

    async def _on_stream_live(event: StreamLiveEvent) -> None:
        logger.info(f"Stream has gone live: {event.broadcaster_name} (ID = {event.broadcaster_id})")

    main_task: Final = asyncio.create_task(run_main_loop(app_state))

    try:
        async with monitor_streams(app_state, _on_stream_live):
            yield
    finally:
        main_task.cancel()
        with suppress(asyncio.CancelledError):
            await main_task


STATIC_FILES_DIRECTORY = Path(__file__).parent.parent.parent / "static"
if not STATIC_FILES_DIRECTORY.exists():
    raise FileNotFoundError(f"Static files directory {STATIC_FILES_DIRECTORY} does not exist.")

app: Final = FastAPI(lifespan=lifespan)
app.include_router(commands.router)
app.include_router(imprint.router)
app.include_router(login.router)
app.include_router(overlay.router)
app.include_router(auth.router)
app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)

if __name__ == "__main__":
    uvicorn.run(app)
