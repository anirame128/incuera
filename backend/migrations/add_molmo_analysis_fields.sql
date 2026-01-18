-- Migration: Add Molmo 2 analysis fields to sessions table
-- Run: psql -d your_database -f migrations/add_molmo_analysis_fields.sql

-- Add analysis status column
ALTER TABLE sessions
ADD COLUMN IF NOT EXISTS analysis_status VARCHAR(20) DEFAULT 'pending';

-- Add analysis completion timestamp
ALTER TABLE sessions
ADD COLUMN IF NOT EXISTS analysis_completed_at TIMESTAMP WITH TIME ZONE;

-- Add interaction heatmap data (JSONB for flexible structure)
ALTER TABLE sessions
ADD COLUMN IF NOT EXISTS interaction_heatmap JSONB;

-- Add conversion funnel data
ALTER TABLE sessions
ADD COLUMN IF NOT EXISTS conversion_funnel JSONB;

-- Add error events data
ALTER TABLE sessions
ADD COLUMN IF NOT EXISTS error_events JSONB;

-- Add session summary (dense caption)
ALTER TABLE sessions
ADD COLUMN IF NOT EXISTS session_summary TEXT;

-- Add action counts
ALTER TABLE sessions
ADD COLUMN IF NOT EXISTS action_counts JSONB;

-- Add Molmo analysis metadata (model version, processing time, confidence scores)
ALTER TABLE sessions
ADD COLUMN IF NOT EXISTS molmo_analysis_metadata JSONB;

-- Create index on analysis_status for efficient filtering
CREATE INDEX IF NOT EXISTS idx_sessions_analysis_status ON sessions(analysis_status)
    WHERE analysis_status IS NOT NULL;

-- Create index on analysis_completed_at for querying analyzed sessions
CREATE INDEX IF NOT EXISTS idx_sessions_analysis_completed_at ON sessions(analysis_completed_at)
    WHERE analysis_completed_at IS NOT NULL;
