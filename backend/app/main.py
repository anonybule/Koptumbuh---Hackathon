from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
from app.config import settings
from app.schemas.common import err


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from app.services.minio_service import ensure_buckets
        ensure_buckets()
    except Exception:
        pass
    yield
    from app.database import engine, simkopdes_engine
    await engine.dispose()
    await simkopdes_engine.dispose()


app = FastAPI(
    title="KopTumbuh API",
    version="1.0.0",
    description="JasaAI — WhatsApp-first cooperative management platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        return JSONResponse(status_code=exc.status_code, content=err(detail["code"], detail.get("message", ""), detail.get("details")))
    message = detail if isinstance(detail, str) else str(detail)
    code = "UNAUTHORIZED" if exc.status_code == 401 else "FORBIDDEN" if exc.status_code == 403 else "ERROR"
    return JSONResponse(status_code=exc.status_code, content=err(code, message))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=err("VALIDATION_ERROR", "Request validation failed", {"errors": exc.errors()}),
    )


@app.get("/health")
async def health():
    statuses = {}
    try:
        from app.database import engine
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        statuses["db"] = "ok"
    except Exception as e:
        statuses["db"] = f"error: {str(e)[:50]}"
    try:
        import redis as r
        rd = r.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        rd.ping()
        statuses["redis"] = "ok"
    except Exception as e:
        statuses["redis"] = f"error: {str(e)[:50]}"
    try:
        from app.services.minio_service import ensure_buckets
        ensure_buckets()
        statuses["minio"] = "ok"
    except Exception as e:
        statuses["minio"] = f"error: {str(e)[:50]}"
    # Evolution is optional (Path B POS works without it)
    try:
        import httpx
        url = (settings.EVOLUTION_API_URL or "").rstrip("/") + "/"
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(url)
        statuses["evolution"] = "ok" if resp.status_code < 500 else f"degraded: HTTP {resp.status_code}"
    except Exception as e:
        statuses["evolution"] = f"unavailable: {str(e)[:40]}"

    core_ok = all(statuses.get(k) == "ok" for k in ("db", "redis", "minio"))
    return {
        "status": "ok" if core_ok else "degraded",
        "team": "JasaAI",
        "services": statuses,
    }


from app.api.v1.router import api_router
app.include_router(api_router, prefix="/api/v1")
