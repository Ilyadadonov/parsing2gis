from aiogram import Router
from .start import router as start_router
from .collect import router as collect_router
from .export import router as export_router

main_router = Router()
main_router.include_router(start_router)
main_router.include_router(collect_router)
main_router.include_router(export_router)
