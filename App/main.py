import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from App.api.routes import router
from App.core.config import Settings
from App.core.logging import configure_logging
from App.core.middleware import OperationsMiddleware
from App.services.pokeapi_client import PokeAPIClient, NotFound, UpstreamUnavailable
from App.services.type_chart import TYPE_CHART

def create_app(settings: Settings | None = None, transport: httpx.AsyncBaseTransport | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with httpx.AsyncClient(
            base_url=str(settings.pokeapi_base_url).rstrip("/") + "/",
            timeout=settings.pokeapi_timeout_seconds,
            limits=httpx.Limits(max_connections=5, max_keepalive_connections=5),
            follow_redirects=False, transport=transport,
        ) as http:
            app.state.pokeapi = PokeAPIClient(settings, http)
            yield

    app = FastAPI(title="Pokemon Weakness and Counter API", version="1.0.0", lifespan=lifespan)
    app.add_middleware(OperationsMiddleware, rate_limit=settings.rate_limit_per_minute)
    app.include_router(router, prefix="/api/v1")

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        logging.getLogger("pokemon").warning("security_event", extra={"status": 422})
        # Do not echo arbitrary input or Pydantic internals to clients.
        return JSONResponse(status_code=422, content={"detail": [
            {"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]}
            for error in exc.errors()
        ]})

    @app.get("/health", tags=["Operations"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready", tags=["Operations"])
    async def ready(request: Request):
        try:
            resource = await request.app.state.pokeapi.get("type", "normal")
            degraded = resource.warning is not None
            return {"status": "degraded" if degraded else "ready", "source": resource.source,
                    "fallback_available": len(TYPE_CHART) == 18,
                    "warnings": [resource.warning] if degraded else []}
        except (NotFound, UpstreamUnavailable):
            return JSONResponse(status_code=503, content={"status": "not_ready"})

    return app


app = create_app()
