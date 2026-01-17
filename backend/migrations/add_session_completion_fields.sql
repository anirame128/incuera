-- Migration: Add session completion fields for grace period handling
-- This migration adds fields needed for the ENDING state with grace period

-- Add ending_started_at: Timestamp when session entered ENDING state
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS ending_started_at TIMESTAMPTZ;

-- Add end_reason: Why session ended (beforeunload, pagehide, stale_cleanup, manual_stop)
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS end_reason VARCHAR(50);

-- Add expected_event_count: Final event count reported by SDK during end signal
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS expected_event_count INTEGER;

-- Add last_event_at: Server-side timestamp of last event received
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS last_event_at TIMESTAMPTZ;

-- Create index on ending_started_at for efficient cleanup queries
CREATE INDEX IF NOT EXISTS idx_sessions_ending_started_at ON sessions(ending_started_at)
    WHERE ending_started_at IS NOT NULL;

-- Create index for finding sessions in ENDING state
CREATE INDEX IF NOT EXISTS idx_sessions_status_ending ON sessions(status)
    WHERE status = 'ending';
