import time
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# Import the core predictive and health routes
from src.api.routes import router

# Configure logging for the application
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize the FastAPI application
app = FastAPI(
    title="RouteTrust API", 
    version="1.0.0", 
    description="Chance-constrained reliable transit routing API"
)

# 1. Add CORS Middleware
# Allows cross-origin requests from any client interface seamlessly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 2. Request Logging & Metrics Middleware
@app.middleware("http")
async def log_requests_and_metrics(request: Request, call_next):
    """
    Intercepts all incoming HTTP requests to log latency and status codes.
    This centralized middleware ensures uniform observability across all endpoints.
    Provides an optimal hook point for future Rate Limiting configurations.
    """
    start_time = time.perf_counter()
    logger.info(f"Incoming Request: {request.method} {request.url.path}")
    
    # Process the request down the stack
    response = await call_next(request)
    
    # Calculate response metrics
    process_time = (time.perf_counter() - start_time) * 1000.0
    logger.info(
        f"Completed Request: {request.method} {request.url.path} "
        f"- Status: {response.status_code} - Latency: {process_time:.2f}ms"
    )
    
    return response


# 3. Application Lifecycle Events
@app.on_event("startup")
async def startup_event():
    """
    Fires when the ASGI server boots the FastAPI application.
    Ideal place to initialize database connection pools or Redis/Memcached if added.
    """
    logger.info("Booting up RouteTrust API...")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Fires when the server receives a termination signal.
    Ideal place to elegantly tear down connections to prevent memory/socket leaks.
    """
    logger.info("Shutting down RouteTrust API safely...")


# 4. Router Inclusion
# Prefix all core endpoints with API version 1 namespace
app.include_router(router, prefix="/api/v1")
