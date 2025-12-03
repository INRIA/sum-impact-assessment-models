"""
FastAPI application instance and configuration.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import kpis
from ..config.settings import settings

# Create FastAPI application
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="API for SUM Impact Assessment - Analyze Living Labs measures and KPIs",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this based on your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(kpis.router, tags=["KPIs"])


@app.on_event("startup")
async def startup_event():
    """
    Application startup event handler.
    """
    print(f"🚀 Starting {settings.API_TITLE} v{settings.API_VERSION}")
    print(f"📊 Database: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    print(f"🌐 API running on http://{settings.API_HOST}:{settings.API_PORT}")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event handler.
    """
    print("👋 Shutting down API server")
