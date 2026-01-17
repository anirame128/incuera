"""Database connection and session management."""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from app.config import settings

# Use NullPool for serverless/auto-scaling deployments (recommended by Supabase)
# This works with Supabase pooler (port 6543)
# For stationary servers, use regular pooling
if settings.environment in ("development", "production"):
    # Check if using pooler connection (recommended)
    if "pooler.supabase.com" in settings.database_url or settings.database_url.endswith(":6543"):
        engine = create_engine(
            settings.database_url,
            poolclass=NullPool,  # Required for pooler connections
            echo=settings.environment == "development",
        )
    else:
        # Direct connection for stationary servers
        engine = create_engine(
            settings.database_url,
            pool_size=20,
            max_overflow=10,
            echo=settings.environment == "development",
        )
else:
    engine = create_engine(
        settings.database_url,
        poolclass=NullPool,
        echo=True,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
