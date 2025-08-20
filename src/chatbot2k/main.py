import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Final

import uvicorn
from fastapi import FastAPI

from chatbot2k.core import run_main_loop
from chatbot2k.routes import commands

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    asyncio.create_task(run_main_loop())
    yield


app: Final = FastAPI(lifespan=lifespan)
app.include_router(commands.router)


if __name__ == "__main__":
    uvicorn.run(app)
