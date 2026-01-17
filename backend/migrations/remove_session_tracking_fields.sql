-- Migration: Remove unused session tracking fields
-- This migration removes fields related to heartbeat, grace period, and ENDING state logic
-- Run: psql -d your_database -f migrations/remove_session_tracking_fields.sql

-- Drop indexes first
DROP INDEX IF EXISTS idx_sessions_last_heartbeat;
DROP INDEX IF EXISTS idx_sessions_ending_started_at;
DROP INDEX IF EXISTS idx_sessions_status_ending;

-- Drop columns that are no longer used
ALTER TABLE sessions
DROP COLUMN IF EXISTS last_heartbeat_at;

ALTER TABLE sessions
DROP COLUMN IF EXISTS ending_started_at;

ALTER TABLE sessions
DROP COLUMN IF EXISTS end_reason;

ALTER TABLE sessions
DROP COLUMN IF EXISTS expected_event_count;

-- Note: last_event_at is kept as it's still used for tracking event timestamps
-- Note: status column is kept but 'ending' is no longer a valid value
-- Valid status values are now: active, completed, processing, ready, failed
