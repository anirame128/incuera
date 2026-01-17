-- Migration: Fix event_timestamp column type from INTEGER to BIGINT
-- JavaScript timestamps (milliseconds) exceed PostgreSQL INTEGER max value (2,147,483,647)

ALTER TABLE events 
ALTER COLUMN event_timestamp TYPE BIGINT;
