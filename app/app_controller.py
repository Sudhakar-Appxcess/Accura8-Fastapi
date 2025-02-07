# ** App Modules
from fastapi import APIRouter
from app.controller.base import router as base_router
from app.controller.auth import router as auth_router
# from app.controller.code_convert import router as code_convert_router
from app.controller.code_converter import router as code_converter_router
from app.controller.sql_migration import router as sql_migration_router
from app.controller.nl_to_sql import router as nl_to_sql_router
from app.controller.pdf_chat import router as pdf_chat_router
from app.controller.database import router as database_router

def register_controller(app):
    api_router = APIRouter(prefix="/api/v1")

    api_router.include_router(base_router,prefix="/base", tags=["Base"])

    api_router.include_router(auth_router,prefix="/auth", tags=["Authentication"])

    api_router.include_router(sql_migration_router, prefix="/sql_m", tags=["SQL Migrations"])
    api_router.include_router(code_converter_router, prefix="/code", tags=["Code Converter"])
    api_router.include_router(nl_to_sql_router, prefix="/sql_n", tags=["Natural Language to SQL"])

    api_router.include_router(pdf_chat_router, prefix="/pdf", tags=["PDF to Natural Chat"])

    api_router.include_router(database_router, prefix="/db", tags=["Databse Querying"])



    app.include_router(api_router)
