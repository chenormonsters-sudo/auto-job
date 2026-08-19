from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .api import deliveries, jobs, platforms, resumes, reviews
from .api.settings import router as settings_router
from .config import settings
from .database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


app.add_middleware(SecurityHeadersMiddleware)

app.include_router(resumes.router)
app.include_router(jobs.router)
app.include_router(reviews.router)
app.include_router(deliveries.router)
app.include_router(platforms.router)
app.include_router(settings_router)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "min_delivery_interval_seconds": settings.min_delivery_interval_seconds,
        "fingerprint_spoofing_enabled": settings.fingerprint_spoofing_enabled,
    }
