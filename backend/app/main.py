from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.modules.donations.router import donations_router
from app.modules.identity.router import router as identity_router
from app.modules.projects.router import (
    admin_projects_router,
    my_projects_router,
    projects_router,
)
from app.shared.config import settings
from app.shared.database import Base, engine
from app.shared.logging import setup_logging


def create_app() -> FastAPI:
    # Initialize structured module logging
    setup_logging(settings.LOG_LEVEL)

    # Ensure database tables exist (for SQLite dev/test)
    Base.metadata.create_all(bind=engine)

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

    # Register module routers
    app.include_router(identity_router, prefix="/api")
    app.include_router(projects_router, prefix="/api")
    app.include_router(my_projects_router, prefix="/api")
    app.include_router(admin_projects_router, prefix="/api")
    app.include_router(donations_router, prefix="/api")
    

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