import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import create_tables

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("DealGuard starting up", env=settings.app_env)
    await create_tables()
    logger.info("Database tables ready")
    yield
    logger.info("DealGuard shutting down")


app = FastAPI(
    title="DealGuard API",
    description=(
        "AI-powered e-commerce price intelligence platform. "
        "Compares current prices against historical data to help users "
        "understand whether a displayed discount is genuinely attractive."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and register routes
from app.api.routes import search, products, history, analysis, chat, offers  # noqa: E402

app.include_router(search.router, prefix="/api/v1", tags=["search"])
app.include_router(products.router, prefix="/api/v1", tags=["products"])
app.include_router(history.router, prefix="/api/v1", tags=["history"])
app.include_router(analysis.router, prefix="/api/v1", tags=["analysis"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(offers.router, prefix="/api/v1", tags=["offers"])


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "service": "dealguard-api", "version": "1.0.0"}
