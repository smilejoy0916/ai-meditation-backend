-- Migration to add elevenlabs_model field to existing admin_settings table
-- Run this if you already have the admin_settings table from the previous version

-- Add the elevenlabs_model column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'admin_settings' 
        AND column_name = 'elevenlabs_model'
    ) THEN
        ALTER TABLE admin_settings 
        ADD COLUMN elevenlabs_model TEXT NOT NULL DEFAULT 'eleven_turbo_v2_5';
        
        RAISE NOTICE 'Column elevenlabs_model added successfully';
    ELSE
        RAISE NOTICE 'Column elevenlabs_model already exists';
    END IF;
END $$;

