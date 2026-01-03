import asyncio
import logging
import signal
from collections.abc import AsyncGenerator
from collections.abc import Callable
from contextlib import asynccontextmanager
from contextlib import suppress
from types import FrameType
from typing import Final
from typing import Optional
from typing import cast

import uvicorn
from fastapi import FastAPI
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from chatbot2k.constants import STATIC_FILES_DIRECTORY
from chatbot2k.core import run_main_loop
from chatbot2k.dependencies import get_app_state
from chatbot2k.dependencies import get_common_context
from chatbot2k.dependencies import get_current_user
from chatbot2k.routes import admin
from chatbot2k.routes import auth
from chatbot2k.routes import commands
from chatbot2k.routes import imprint
from chatbot2k.routes import login
from chatbot2k.routes import overlay
from chatbot2k.routes import viewer
from chatbot2k.types.template_contexts import ErrorContext

logging.basicConfig(level=logging.INFO)


logger: Final = logging.getLogger(__name__)

type _SignalHandler = Callable[[int, Optional[FrameType]], None]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    app_state: Final = get_app_state()
    main_task: Final = asyncio.create_task(run_main_loop(app_state))

    original_handlers: Final[dict[int, _SignalHandler]] = {
        signal.SIGINT: cast(_SignalHandler, signal.signal(signal.SIGINT, signal.SIG_DFL)),
        signal.SIGTERM: cast(_SignalHandler, signal.signal(signal.SIGTERM, signal.SIG_DFL)),
    }

    def _handle_shutdown_signal(sig: int, frame: Optional[FrameType]) -> None:
        logger.info(f"Received shutdown signal {sig}, setting shutdown event")
        app_state.shut_down()
        # Call the original handler to allow Uvicorn to proceed with shutdown.
        original_handler: Final = original_handlers.get(sig)
        if original_handler is None:
            raise AssertionError
        if callable(original_handler):
            original_handler(sig, frame)
        else:
            logger.error(f"Original handler for signal {sig} is not callable")

    # Set up signal handlers for graceful shutdown.
    for sig in original_handlers:
        signal.signal(sig, _handle_shutdown_signal)

    try:
        yield
    finally:
        # Ensure shutdown event is set (in case shutdown wasn't triggered by signal)
        app_state.shut_down()
        main_task.cancel()
        with suppress(asyncio.CancelledError):
            await main_task


if not STATIC_FILES_DIRECTORY.exists():
    raise FileNotFoundError(f"Static files directory {STATIC_FILES_DIRECTORY} does not exist.")

app: Final = FastAPI(lifespan=lifespan)

templates: Final = Jinja2Templates(directory="templates")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> Response:
    """Handle HTTP exceptions by rendering an error page instead of JSON."""
    app_state: Final = get_app_state()
    common_context: Final = await get_common_context(get_current_user(request, app_state), app_state)

    context: Final = ErrorContext(
        **common_context.model_dump(),
        error_detail=exc.detail,
    )

    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context=context.model_dump(),
        status_code=exc.status_code,
    )


app.include_router(commands.router)
app.include_router(imprint.router)
app.include_router(login.router)
app.include_router(overlay.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(viewer.router)
app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)

if __name__ == "__main__":
    uvicorn.run(app)
