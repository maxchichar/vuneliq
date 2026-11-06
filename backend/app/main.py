from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.modules.identity.models
import app.modules.projects.models
from app.modules.identity.router import router as identity_router
from app.modules.projects.router import (
    admin_projects_router,
    my_projects_router,
    projects_router,
)
from app.shared.config import settings
from app.shared.database import Base, engine


def create_app() -> FastAPI:
    # Ensure database tables exist (for AQLite dev/test)
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