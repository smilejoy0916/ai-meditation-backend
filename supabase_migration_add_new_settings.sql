-- Migration: Add new settings columns to admin_settings table
-- Description: Adds chapter_count, silence_duration_seconds, user_password, and admin_password

-- Add chapter_count column (number of chapters to split meditation into)
ALTER TABLE admin_settings 
ADD COLUMN IF NOT EXISTS chapter_count INTEGER DEFAULT 3;

-- Add silence_duration_seconds column (duration of silence between chapters)
ALTER TABLE admin_settings 
ADD COLUMN IF NOT EXISTS silence_duration_seconds INTEGER DEFAULT 45;

-- Add user_password column (password for regular user access)
ALTER TABLE admin_settings 
ADD COLUMN IF NOT EXISTS user_password TEXT DEFAULT 'user';

-- Add admin_password column (password for admin access)
ALTER TABLE admin_settings 
ADD COLUMN IF NOT EXISTS admin_password TEXT DEFAULT 'admin';

-- Add comments for documentation
COMMENT ON COLUMN admin_settings.chapter_count IS 'Number of chapters to split meditation into (affects number of break tags)';
COMMENT ON COLUMN admin_settings.silence_duration_seconds IS 'Duration of silence between chapters in seconds';
COMMENT ON COLUMN admin_settings.user_password IS 'Password for regular user authentication';
COMMENT ON COLUMN admin_settings.admin_password IS 'Password for admin authentication';

