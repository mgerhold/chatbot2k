import asyncio
import logging

from chatbot2k.core import run_main_loop

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    await run_main_loop()


if __name__ == "__main__":
    asyncio.run(main())
