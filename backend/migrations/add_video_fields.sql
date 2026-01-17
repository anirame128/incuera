-- Migration: Add video generation fields to sessions table
-- Run: psql -d your_database -f migrations/add_video_fields.sql

-- Add session status column
ALTER TABLE sessions
ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active';

-- Add video-related columns
ALTER TABLE sessions
ADD COLUMN IF NOT EXISTS video_url VARCHAR(500);

ALTER TABLE sessions
ADD COLUMN IF NOT EXISTS video_thumbnail_url VARCHAR(500);

ALTER TABLE sessions
ADD COLUMN IF NOT EXISTS keyframes_url VARCHAR(500);

ALTER TABLE sessions
ADD COLUMN IF NOT EXISTS video_generated_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE sessions
ADD COLUMN IF NOT EXISTS video_duration_ms INTEGER;

ALTER TABLE sessions
ADD COLUMN IF NOT EXISTS video_size_bytes BIGINT;

ALTER TABLE sessions
ADD COLUMN IF NOT EXISTS last_heartbeat_at TIMESTAMP WITH TIME ZONE;

-- Create index on status for efficient filtering
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);

-- Create index on last_heartbeat_at for stale session detection
CREATE INDEX IF NOT EXISTS idx_sessions_last_heartbeat ON sessions(last_heartbeat_at);

-- Update existing sessions to have 'completed' status (since they have no heartbeat)
UPDATE sessions
SET status = 'completed'
WHERE status IS NULL OR status = 'active';
