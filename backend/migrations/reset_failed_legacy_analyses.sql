-- Reset failed analyses that have legacy errors (torch/transformers/accelerate)
-- This allows them to be retried with the new API-only code

UPDATE sessions
SET 
    analysis_status = 'pending',
    molmo_analysis_metadata = NULL,
    analysis_completed_at = NULL
WHERE 
    analysis_status = 'failed'
    AND molmo_analysis_metadata IS NOT NULL
    AND (
        molmo_analysis_metadata::text ILIKE '%device_map%'
        OR molmo_analysis_metadata::text ILIKE '%accelerate%'
        OR molmo_analysis_metadata::text ILIKE '%torch%'
        OR molmo_analysis_metadata::text ILIKE '%transformers%'
        OR molmo_analysis_metadata::text ILIKE '%from_pretrained%'
    );

-- Also reset any failed analyses where all analysis fields are empty
-- (these might have failed for other reasons but should be retried)
UPDATE sessions
SET 
    analysis_status = 'pending',
    molmo_analysis_metadata = NULL,
    analysis_completed_at = NULL
WHERE 
    analysis_status = 'failed'
    AND video_url IS NOT NULL
    AND session_summary IS NULL
    AND interaction_heatmap IS NULL
    AND conversion_funnel IS NULL
    AND error_events IS NULL
    AND action_counts IS NULL;
