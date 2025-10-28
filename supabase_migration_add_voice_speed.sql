-- Add elevenlabs_speed column to admin_settings table
ALTER TABLE admin_settings 
ADD COLUMN IF NOT EXISTS elevenlabs_speed DECIMAL(2, 1) NOT NULL DEFAULT 0.7;

-- Add constraint to ensure speed is between 0.7 and 1.2
ALTER TABLE admin_settings 
ADD CONSTRAINT elevenlabs_speed_range CHECK (elevenlabs_speed >= 0.7 AND elevenlabs_speed <= 1.2);

