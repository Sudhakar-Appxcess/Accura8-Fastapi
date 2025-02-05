# ** App Modules
from fastapi import APIRouter
from app.controller.base import router as base_router
from app.controller.auth import router as auth_router
from app.controller.code_convert import router as code_convert_router
def register_controller(app):
    api_router = APIRouter(prefix="/api/v1")

    api_router.include_router(base_router,prefix="/base", tags=["Base"])
    api_router.include_router(auth_router,prefix="/auth", tags=["Authentication"])
    api_router.include_router(code_convert_router, prefix="/api/code", tags=["code"])

    app.include_router(api_router)
