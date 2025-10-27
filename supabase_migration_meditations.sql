-- Create meditations table
CREATE TABLE IF NOT EXISTS meditations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE,
    disease TEXT NOT NULL,
    symptom TEXT NOT NULL,
    additional_instructions TEXT,
    meditation_text TEXT NOT NULL,
    audio_url TEXT,
    duration_seconds INTEGER,
    status TEXT NOT NULL DEFAULT 'completed',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Create index on session_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_meditations_session_id ON meditations(session_id);

-- Create index on created_at for sorting
CREATE INDEX IF NOT EXISTS idx_meditations_created_at ON meditations(created_at DESC);

-- Create updated_at trigger for meditations table
CREATE TRIGGER update_meditations_updated_at
    BEFORE UPDATE ON meditations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security (RLS)
ALTER TABLE meditations ENABLE ROW LEVEL SECURITY;

-- Create policy to allow all operations (adjust based on your security needs)
CREATE POLICY "Allow all operations on meditations"
    ON meditations
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Note: In production, you might want to restrict access based on authentication
