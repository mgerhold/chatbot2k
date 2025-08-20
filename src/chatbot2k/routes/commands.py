from typing import Final

from fastapi.routing import APIRouter

router: Final = APIRouter()


@router.get("/commands")
def show_commands():
    return "Hello, world!"
