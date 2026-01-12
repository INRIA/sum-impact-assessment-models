"""
FastAPI application instance and configuration.
"""
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from .routes import kpis, jobs, simulation, health
from ..config.settings import settings
from ..utils.logger import get_logger
from ..database.connection import Base, engine

# Initialize logger
logger = get_logger(__name__)

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


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware to log all HTTP requests and responses.
    """
    start_time = time.time()

    # Log incoming request
    logger.info(
        "Incoming request",
        extra={
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "client_host": request.client.host if request.client else None
        }
    )

    # Process request
    response = await call_next(request)

    # Calculate processing time
    process_time = time.time() - start_time

    # Log response
    logger.info(
        "Request completed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time_ms": round(process_time * 1000, 2)
        }
    )

    # Add processing time to response headers
    response.headers["X-Process-Time"] = str(process_time)

    return response


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(kpis.router, tags=["KPIs"])
app.include_router(jobs.router, tags=["Jobs"])
app.include_router(simulation.router, tags=["Simulation (NON-prod only)⚠️"])


@app.on_event("startup")
async def startup_event():
    """
    Application startup event handler.
    """
    # Create database tables if they don't exist
    logger.info("Creating database tables if they don't exist")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")

    logger.info(
        "API server starting",
        extra={
            "event": "startup",
            "api_title": settings.API_TITLE,
            "api_version": settings.API_VERSION,
            "db_host": settings.DB_HOST,
            "db_port": settings.DB_PORT,
            "db_name": settings.DB_NAME,
            "api_host": settings.API_HOST,
            "api_port": settings.API_PORT
        }
    )


@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event handler.
    """
    logger.info("API server shutting down", extra={"event": "shutdown"})
