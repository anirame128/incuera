-- Add slug column to projects table
ALTER TABLE projects ADD COLUMN IF NOT EXISTS slug VARCHAR;

-- Create index on slug for faster lookups
CREATE INDEX IF NOT EXISTS idx_projects_slug ON projects(slug);

-- Generate slugs for existing projects
-- Slug format: lowercase, replace spaces with hyphens, remove special chars
UPDATE projects
SET slug = LOWER(
    REGEXP_REPLACE(
        REGEXP_REPLACE(name, '[^a-zA-Z0-9\s-]', '', 'g'),
        '\s+', '-', 'g'
    )
)
WHERE slug IS NULL;

-- Make slug NOT NULL after populating existing data
ALTER TABLE projects ALTER COLUMN slug SET NOT NULL;

-- Add unique constraint on (user_id, slug) to ensure slugs are unique per user
CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_user_slug ON projects(user_id, slug);
