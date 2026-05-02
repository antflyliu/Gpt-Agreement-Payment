import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from .backend.errors import PreflightError
from .backend.routes import setup as setup_routes
from .backend.routes import auth as auth_routes
from .backend.routes import wizard as wizard_routes
from .backend.routes import preflight as preflight_routes
from .backend.routes import sniff as sniff_routes
from .backend.routes import config as config_routes
from .backend.routes import run as run_routes
from .backend.routes import whatsapp as whatsapp_routes

logger = logging.getLogger("webui")

FRONTEND_DIST = Path(__file__).parent / "frontend" / "dist"


def _setup_logging() -> None:
    """Configure consistent log format for all webui.* loggers."""
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-5s %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler = logging.StreamHandler()
    handler.setFormatter(fmt)
    root = logging.getLogger("webui")
    if not root.handlers:
        root.addHandler(handler)
        root.setLevel(logging.INFO)
        root.propagate = False


def create_app() -> FastAPI:
    _setup_logging()
    app = FastAPI(title="Gpt-Agreement-Payment webui")

    @app.exception_handler(PreflightError)
    async def _preflight_error_handler(request, exc: PreflightError):
        logger.warning("PreflightError %s: %s", exc.code, exc.msg)
        return JSONResponse(
            status_code=422,
            content={
                "status": "fail",
                "code": exc.code,
                "message": exc.msg,
                "hint": exc.hint,
                "checks": [],
            },
        )

    @app.exception_handler(ValidationError)
    async def _validation_error_handler(request, exc: ValidationError):
        logger.warning("ValidationError: %s", exc)
        errors = exc.errors()
        first = errors[0] if errors else {}
        field = ".".join(str(loc) for loc in first.get("loc", []))
        return JSONResponse(
            status_code=422,
            content={
                "status": "fail",
                "code": "validation_error",
                "message": f"{field}: {first.get('msg', str(exc))}",
                "hint": "Check the input fields and try again.",
                "checks": [],
            },
        )

    app.include_router(setup_routes.router)
    app.include_router(auth_routes.router)
    app.include_router(wizard_routes.router)
    app.include_router(preflight_routes.router)
    app.include_router(sniff_routes.router)
    app.include_router(config_routes.router)
    app.include_router(run_routes.router)
    app.include_router(whatsapp_routes.router)

    @app.get("/api/healthz")
    def healthz():
        return {"status": "ok"}

    if FRONTEND_DIST.exists():
        assets_dir = FRONTEND_DIST / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/{full_path:path}")
        def spa(full_path: str):
            if full_path.startswith("api/"):
                # Should not reach here — APIRouters claim /api/* — but guard just in case
                return FileResponse(FRONTEND_DIST / "index.html", status_code=404)
            f = FRONTEND_DIST / full_path
            try:
                f.resolve().relative_to(FRONTEND_DIST.resolve())
            except ValueError:
                # Path escapes dist — serve index.html instead
                return FileResponse(FRONTEND_DIST / "index.html")
            if f.is_file():
                return FileResponse(f)
            return FileResponse(FRONTEND_DIST / "index.html")

    return app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(create_app(), host="0.0.0.0", port=8765)
