from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.shared.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="Vuneliq - Transparent Giving and Impact Tracking API"
    )

    # Configure CORS for frontend access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["System"])
    def healh_check():
        """Health check endpoint used by development checks and monitoring."""
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "environment": settings.ENVIRONMENT,
        }

    return app

app = create_app()