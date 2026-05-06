import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
from .backend.routes import inventory as inventory_routes
from .backend.routes import run as run_routes
from .backend.routes import codex_tokens as codex_tokens_routes
from .backend.routes import cloudflare_kv as cf_kv_routes
from .backend.routes import whatsapp as whatsapp_routes
from .backend.routes import link_state as link_state_routes
from .backend.routes import proxy as proxy_routes
from .backend.routes import auto_loop as auto_loop_routes

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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:8765", "http://localhost:8765"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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

    routers = (
        setup_routes.router,
        auth_routes.router,
        wizard_routes.router,
        preflight_routes.router,
        sniff_routes.router,
        config_routes.router,
        inventory_routes.router,
        run_routes.router,
        codex_tokens_routes.router,
        cf_kv_routes.router,
        whatsapp_routes.router,
        link_state_routes.router,
        proxy_routes.router,
        auto_loop_routes.router,
    )
    for prefix in ("", "/webui"):
        for router in routers:
            app.include_router(router, prefix=prefix)

    @app.get("/webui/api/healthz")
    @app.get("/api/healthz")
    def healthz():
        return {"status": "ok"}

    if FRONTEND_DIST.exists():
        assets_dir = FRONTEND_DIST / "assets"
        if assets_dir.exists():
            # Mount under both / and /webui/ so the same build serves direct
            # (127.0.0.1:8765/) and reverse-proxied (.../webui/) deployments.
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
            app.mount("/webui/assets", StaticFiles(directory=assets_dir), name="assets_webui")

        def _serve(full_path: str):
            if full_path.startswith("api/"):
                return FileResponse(FRONTEND_DIST / "index.html", status_code=404)
            cleaned = full_path.removeprefix("webui/") if full_path.startswith("webui/") else full_path
            f = FRONTEND_DIST / cleaned
            try:
                f.resolve().relative_to(FRONTEND_DIST.resolve())
            except ValueError:
                return FileResponse(FRONTEND_DIST / "index.html")
            if f.is_file():
                return FileResponse(f)
            return FileResponse(FRONTEND_DIST / "index.html")

        @app.get("/webui/{full_path:path}")
        def spa_webui(full_path: str):
            return _serve(full_path)

        @app.get("/{full_path:path}")
        def spa(full_path: str):
            return _serve(full_path)

    return app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(create_app(), host="127.0.0.1", port=8765)
