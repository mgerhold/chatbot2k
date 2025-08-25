import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Annotated
from typing import Final
from uuid import uuid4

from fastapi import APIRouter
from fastapi import Depends
from starlette.requests import Request
from starlette.responses import Response
from starlette.responses import StreamingResponse
from starlette.templating import Jinja2Templates

from chatbot2k.app_state import AppState
from chatbot2k.dependencies import get_app_state
from chatbot2k.dependencies import get_templates
from chatbot2k.models.soundboard_event import SoundboardEvent
from chatbot2k.utils.sse import sse_encode

router: Final = APIRouter()


@router.get("/overlay")
async def overlay(
    request: Request,
    templates: Annotated[Jinja2Templates, Depends(get_templates)],
) -> Response:
    return templates.TemplateResponse(
        request=request,
        name="overlay.html",
    )


@router.get("/overlay/events", name="overlay_events")
async def overlay_events(
    request: Request,
    app_state: Annotated[AppState, Depends(get_app_state)],
) -> StreamingResponse:
    async def _generate() -> AsyncIterator[bytes]:
        uuid: Final = uuid4()
        logging.info(f"Client connected to `/overlay/events` with UUID {uuid}")
        app_state.soundboard_clips_url_queues[uuid] = asyncio.Queue()
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    clip_url = await asyncio.wait_for(app_state.soundboard_clips_url_queues[uuid].get(), timeout=2.0)
                except TimeoutError:
                    # No new soundboard clips, continue waiting.
                    continue
                yield sse_encode(
                    SoundboardEvent(
                        clip_url=clip_url,
                    )
                ).encode("utf-8")
        except asyncio.CancelledError:
            # Client went away, stop sending events.
            pass
        finally:
            logging.info(f"Client disconnected from `/overlay/events` with UUID {uuid}")
            del app_state.soundboard_clips_url_queues[uuid]

    headers: Final = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",  # If behind nginx, prevents buffering.
    }
    return StreamingResponse(_generate(), media_type="text/event-stream", headers=headers)
