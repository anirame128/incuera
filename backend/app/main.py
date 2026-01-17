"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import ingest, sessions, auth, projects, api_keys, videos
from app.database import Base, engine

# Create database tables (in production, use migrations)
# Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Incuera API",
    description="Backend API for Incuera session replay analytics",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ingest.router)
app.include_router(sessions.router)
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(api_keys.router)
app.include_router(videos.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Incuera API",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
