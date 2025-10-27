-- Migration to add elevenlabs_voice_id field to existing admin_settings table
-- Run this if you already have the admin_settings table from the previous version

-- Add the elevenlabs_voice_id column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'admin_settings' 
        AND column_name = 'elevenlabs_voice_id'
    ) THEN
        ALTER TABLE admin_settings 
        ADD COLUMN elevenlabs_voice_id TEXT NOT NULL DEFAULT 'BpjGufoPiobT79j2vtj4';
        
        RAISE NOTICE 'Column elevenlabs_voice_id added successfully';
    ELSE
        RAISE NOTICE 'Column elevenlabs_voice_id already exists';
    END IF;
END $$;
