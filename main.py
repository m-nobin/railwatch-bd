# main.py - Simplified FastAPI application
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import utility functions
from functions.data_loader import load_data
from functions.redis_tracker import RedisTrainTracker
from functions.route_calculator import (
    precalculate_train_routes,
    precalculate_station_distances,
    precalculate_two_train_routes
)

# Import URL handlers
from urls import github, data, positions, routes, reports, live


# Global variables
DATA, CURRENT_REVISION = load_data()
TWO_TRAIN_ROUTES = {}
TRAIN_ROUTES = {}
STATION_DISTANCES = {}

# Configuration from environment variables
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
TTL_SECONDS = int(os.getenv("TTL_SECONDS", "600"))
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")

# Redis-based train tracker (replaces AsyncTimedStack)
tracker = RedisTrainTracker(
    host=REDIS_HOST, 
    port=REDIS_PORT, 
    db=REDIS_DB, 
    ttl_seconds=TTL_SECONDS
)
tracker.set_train_data(DATA)  # Provide train schedule data for scheduled position calculation

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    global TWO_TRAIN_ROUTES, TRAIN_ROUTES, STATION_DISTANCES
    
    logger.info("Starting Find My BR Train FastAPI Server...")
    logger.info("API Base URL: train.sportsprime.live")
    logger.info("Health Check: train.sportsprime.live/health")
    logger.info("\nPress Ctrl+C to stop the server\n")
    
    # Check Redis connection - fail fast if Redis is unavailable
    if tracker.health_check():
        logger.info("✓ Redis connection established")
    else:
        logger.error("X Redis connection failed - position tracking won't work!")
        raise RuntimeError("Redis connection failed - cannot start server without Redis")
    
    # Precalculate routes and distances
    logger.info("Precalculating train routes...")
    TRAIN_ROUTES = precalculate_train_routes(DATA)
    logger.info("Precalculating station distances...")
    STATION_DISTANCES = precalculate_station_distances(DATA)
    
    logger.info("\n" + "="*60)
    logger.info("INITIALIZING TWO-TRAIN ROUTE PRECALCULATION")
    logger.info("="*60)
    TWO_TRAIN_ROUTES = precalculate_two_train_routes(DATA, CURRENT_REVISION)
    logger.info("="*60 + "\n")
    
    yield
    
    logger.info("Shutting down FastAPI Server...")


app = FastAPI(
    title="Find My BR Train Server",
    description="API server for Find My BR Train app",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
# Security: Configure CORS based on environment variable
# In production, set ALLOWED_ORIGINS to specific domains
if ALLOWED_ORIGINS == "*":
    logger.warning("CORS configured to allow all origins (*) - not recommended for production")
    allowed_origins = ["*"]
else:
    allowed_origins = [origin.strip() for origin in ALLOWED_ORIGINS.split(",")]
    logger.info(f"CORS configured for origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============= ROUTES =============

# GitHub webhook
@app.post("/payload")
async def github_webhook_handler(request: Request):
    return await github.github_webhook(request)


# Data endpoints
@app.get("/initrevision")
async def get_revision():
    return data.get_revision(CURRENT_REVISION)


@app.get("/alltrains")
async def get_all_trains():
    return data.get_all_trains(DATA)


# Position endpoints
@app.get("/current/{train_ids}")
async def get_current_positions_handler(train_ids: str):
    return positions.get_current_positions(train_ids, tracker)


@app.get("/bounds/{train_id}")
async def get_train_bounds_handler(train_id: str):
    """Get current bounds for a train (set by bot users)"""
    return positions.get_train_bounds(train_id, tracker)


@app.post("/sendupdate")
async def receive_update_handler(update: positions.LocationUpdate):
    return positions.receive_update(update, tracker)


# Route endpoints
@app.get("/two-train-routes/{from_station}/{to_station}")
async def get_two_train_routes_handler(from_station: str, to_station: str):
    return routes.get_two_train_routes(from_station, to_station, TWO_TRAIN_ROUTES, DATA)


@app.get("/two-train-routes-all")
async def get_all_two_train_routes_handler():
    return routes.get_all_two_train_routes(TWO_TRAIN_ROUTES, DATA)


@app.post("/nearbyroute")
async def find_nearby_routes_handler(request: routes.NearbyRouteRequest):
    return await routes.find_nearby_routes(request, DATA, TRAIN_ROUTES, STATION_DISTANCES)


# Report endpoints
@app.post("/fix")
async def report_issue_handler(report: reports.IssueReport):
    return await reports.report_issue_post(report)


@app.get("/report")
async def view_reports_handler():
    return await reports.view_reports()


# Live endpoints
@app.get("/health")
async def health_check_handler():
    return live.health_check(CURRENT_REVISION, tracker)


@app.get("/live")
async def view_live_trains_handler():
    return live.view_live_trains(tracker, DATA)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Find My BR Train FastAPI Server",
        "version": "1.0.0",
        "framework": "FastAPI",
        "endpoints": {
            "/initrevision": "GET - Check data revision",
            "/alltrains": "GET - Download complete database",
            "/current/{train_ids}": "GET - Get current train positions",
            "/sendupdate": "POST - Submit location update",
            "/fix": "POST - Report incorrect information",
            "/report": "GET - View all issue reports",
            "/nearbyroute": "POST - Find alternative routes",
            "/health": "GET - Server health check",
            "/live": "GET - View live trains",
            "/docs": "GET - Interactive API documentation",
        },
        "github": "https://github.com/jisangain/find-my-br-train",
        "contribute": "Visit our GitHub repository to contribute!"
    }


if __name__ == '__main__':
    # Get server configuration from environment
    SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
    
    uvicorn.run(
        "main:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=False,
        log_level="info"
    )
