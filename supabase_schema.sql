-- Create admin_settings table
CREATE TABLE IF NOT EXISTS admin_settings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    openai_api_key TEXT NOT NULL DEFAULT '',
    elevenlabs_api_key TEXT NOT NULL DEFAULT '',
    openai_model TEXT NOT NULL DEFAULT 'gpt-4o-mini',
    elevenlabs_model TEXT NOT NULL DEFAULT 'eleven_turbo_v2_5',
    system_prompt TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = TIMEZONE('utc'::text, NOW());
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for admin_settings
CREATE TRIGGER update_admin_settings_updated_at
    BEFORE UPDATE ON admin_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert default settings (optional)
INSERT INTO admin_settings (openai_api_key, elevenlabs_api_key, openai_model, elevenlabs_model, system_prompt)
VALUES (
    '', -- Add your OpenAI API key here
    '', -- Add your ElevenLabs API key here
    'gpt-4o-mini',
    'eleven_turbo_v2_5',
    '#Instruction: write a 10-minute meditation following the below structure. In that meditation, include elevenlabs tags such as [inhale], [exhale], [pause] or [whisper]. To not make it too fast paced, make sure to include a [pause 2 seconds] tag after each sentence. Using "..." also slows the pace down. Take the user inputs into account in the relevant parts of the meditation, as described. Avoid using "now" too much to progress the meditation forward.

#User input:
##Disease: {disease}
##Symptom: {symptom}
##Additional instruction: {additional_instructions}

#Output: output only the meditation itself with the relevant tags, without saying anything else or without including section titles

#Structure of the meditation with instructions for each section:
##Section 1: Introduction to the topic. The general topic is quantum healing. Select a topic at random addressed by Deepak Chopra in his Quantum Healing book without mentioning that book in the meditation. Tie in this general topic with the disease, symptom and additional instruction given by the user above. This part should be suitable for a meditation, yet scientific enough - without being too specific (e.g. there is a proven mind-body connection, but don''t talk about peptides or other detailed processes, just give examples relevant to the disease and symptom)

##Section 2: start of the meditation, settle the user. Choose any of common techniques to do so (e.g. focus on breath, senses, body, etc.). Leave some extra time/silence at the end of this section to allow the user to relax further in silence. End this section with the following tag: <break>

##Section 3: further relaxation. Choose any of common techniques to do so. Leave some extra time/silence at the end of this section to allow the user to relax further in silence. End this section with the following tag: <break>

##Section 4: visualisation. Introduce the visualisation technique, tie it to the disease, symptom and additional instruction of the user and to section 1 of the meditation and then start. Choose any of common visualisation techniques to do so.

##Section 5: end of meditation.'
)
ON CONFLICT DO NOTHING;

-- Enable Row Level Security (RLS)
ALTER TABLE admin_settings ENABLE ROW LEVEL SECURITY;

-- Create policy to allow all operations (adjust based on your security needs)
CREATE POLICY "Allow all operations on admin_settings"
    ON admin_settings
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Note: You should adjust the RLS policies based on your authentication setup
-- For production, you might want to restrict access to authenticated admin users only

