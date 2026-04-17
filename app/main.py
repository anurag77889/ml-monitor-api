import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.models import Alert, MLModel, Prediction, User  # noqa: F401
from app.routers import alerts, auth, models, predictions

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME}")
    logger.info(f"DEBUG={settings.DEBUG}")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified")
    yield
    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}")


def get_application() -> FastAPI:
    application = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        docs_url="/docs" if settings.DEBUG else None,
        # hide docs in production
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # Tighten CORS in production — only allow your frontend origin
    origins = ["*"] if settings.DEBUG else [
        # Add your frontend URL here e.g:
        # "https://your-frontend.vercel.app",
        "*"  # change this once you have a frontend URL
    ]

    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(auth.router)
    application.include_router(models.router)
    application.include_router(predictions.router)
    application.include_router(alerts.router)

    return application


app = get_application()


@app.get("/", tags=["Health"])
def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "debug": settings.DEBUG,
    }


@app.get("/health", tags=["Health"])
def health():
    """
    Dedicated health check endpoint.
    Railway/Render ping this to verify the service is alive.
    """
    return {"status": "healthy"}
