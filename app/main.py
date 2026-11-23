import json
import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException

from .catalog import CatalogStore, CategoryPage
from .database import DatabaseUnavailable, PostgresCatalog

logger = logging.getLogger("uvicorn.error")


class Health(BaseModel):
    status: str


class Problem(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorEnvelope(BaseModel):
    error: Problem


def problem(request, status, code, message):
    return JSONResponse({"error": {"code": code, "message": message,
                                   "request_id": request.state.request_id}}, status_code=status)


def create_app(store: CatalogStore | None = None):
    api = FastAPI(title="Clothing commerce foundation", version="0.1.0")
    catalog = store if store is not None else PostgresCatalog()

    @api.middleware("http")
    async def request_log(request: Request, call_next):
        request.state.request_id = str(uuid4())
        started = time.monotonic()
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error(json.dumps({"event": "request_failure", "type": type(exc).__name__,
                                     "request_id": request.state.request_id}))
            response = problem(request, 500, "internal_error", "Request could not be completed.")
        response.headers["X-Request-ID"] = request.state.request_id
        route = request.scope.get("route")
        logger.info(json.dumps({"request_id": request.state.request_id, "method": request.method,
                                "route": getattr(route, "path", "unmatched"),
                                "status": response.status_code,
                                "duration_ms": round((time.monotonic()-started)*1000)}))
        return response

    @api.exception_handler(RequestValidationError)
    async def validation(request, exc):
        return problem(request, 422, "invalid_input", "Check the required fields and allowed values.")

    @api.exception_handler(DatabaseUnavailable)
    async def unavailable(request, exc):
        return problem(request, 503, "database_unavailable", "The catalog is temporarily unavailable.")

    @api.exception_handler(HTTPException)
    async def http_error(request, exc):
        response = problem(request, exc.status_code, "http_error", "The requested operation is unavailable.")
        response.headers.update(exc.headers or {})
        return response

    @api.get("/health/live", response_model=Health)
    def live():
        return {"status": "alive"}

    @api.get("/health/ready", response_model=Health, responses={503: {"model": ErrorEnvelope}})
    def ready():
        if not catalog.ready():
            raise DatabaseUnavailable()
        return {"status": "ready"}

    @api.get("/api/v1/categories", response_model=CategoryPage,
             responses={422: {"model": ErrorEnvelope}, 503: {"model": ErrorEnvelope}})
    def categories(page: int = Query(1, ge=1, le=1000000), page_size: int = Query(24, ge=1, le=100)):
        return {"items": catalog.categories(page, page_size), "page": page, "page_size": page_size}

    return api


app = create_app()
