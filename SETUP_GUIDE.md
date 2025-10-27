# Admin Page Setup Guide

This guide will help you set up the admin page with Supabase integration for managing API keys, models, and system prompts.

## Features

The admin page allows you to manage:

- OpenAI API Key
- OpenAI Model selection (GPT-4o Mini, GPT-4o, GPT-4 Turbo, etc.)
- ElevenLabs API Key
- ElevenLabs Model selection (Turbo v2.5, Turbo v2, Multilingual v2, etc.)
- System Prompt Template

## Setup Instructions

### 1. Create a Supabase Project

1. Go to [Supabase](https://supabase.com) and create a new account or log in
2. Create a new project
3. Wait for the project to be fully initialized

### 2. Set Up the Database

1. In your Supabase dashboard, go to the **SQL Editor**
2. Copy the contents of `backend/supabase_schema.sql`
3. Paste it into the SQL Editor and run the query
4. This will create the `admin_settings` table with the necessary structure

### 3. Get Your Supabase Credentials

1. In your Supabase dashboard, go to **Project Settings** > **API**
2. Copy the following values:
   - **Project URL** (e.g., `https://xxxxxxxxxxxxx.supabase.co`)
   - **anon/public key** (the public API key)

### 4. Configure Backend Environment Variables

1. Navigate to the `backend` directory
2. Copy `env.example` to `.env`:
   ```bash
   cp env.example .env
   ```
3. Update the `.env` file with your Supabase credentials:
   ```
   SUPABASE_URL=your_supabase_project_url_here
   SUPABASE_KEY=your_supabase_anon_key_here
   ```

### 5. Install Backend Dependencies

Make sure you have the new dependencies installed:

```bash
cd backend
pip install -r requirements.txt
```

### 6. Configure Frontend Environment Variables (Optional)

If you need to change the API URL:

1. Navigate to the `frontend` directory
2. Create a `.env.local` file if it doesn't exist
3. Add:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

### 7. Start the Application

**Backend:**

```bash
cd backend
python main.py
```

**Frontend:**

```bash
cd frontend
npm run dev
```

### 8. Access the Admin Page

1. Log in to the application at `http://localhost:3000`
2. After authentication, you'll see a "Settings" button in the top-right corner of the Create page
3. Click the "Settings" button to access the admin page
4. Configure your API keys and system prompt
5. Click "Save Settings" to store them in Supabase

## How It Works

### Backend

- The `services/supabase_service.py` handles all database interactions
- Settings are fetched from Supabase when generating meditations
- If Supabase is unavailable, the system falls back to environment variables
- API endpoints:
  - `GET /api/admin/settings` - Retrieve current settings
  - `PUT /api/admin/settings` - Update settings

### Frontend

- The admin page is located at `/admin`
- It provides a clean UI to manage all configuration
- Settings are saved directly to Supabase
- The admin page can be accessed from the Create page via the Settings button

## Security Considerations

### Current Setup (Development)

The current setup has permissive RLS (Row Level Security) policies that allow all operations. This is suitable for development.

### For Production

You should:

1. **Enable Authentication**: Set up Supabase Authentication
2. **Update RLS Policies**: Restrict access to authenticated admin users only
3. **Add Admin Role**: Create an admin role/flag in your user table
4. **Update Policies**: Modify the RLS policy in the SQL schema:

```sql
-- Example: Restrict to authenticated admin users
CREATE POLICY "Admin users only"
    ON admin_settings
    FOR ALL
    USING (auth.role() = 'authenticated' AND auth.jwt() ->> 'user_role' = 'admin')
    WITH CHECK (auth.role() = 'authenticated' AND auth.jwt() ->> 'user_role' = 'admin');
```

5. **Secure the Backend Endpoint**: Add authentication middleware to the admin endpoints in `main.py`

## Troubleshooting

### "SUPABASE_URL and SUPABASE_KEY must be set in environment variables"

- Make sure you've created a `.env` file in the backend directory
- Verify that `SUPABASE_URL` and `SUPABASE_KEY` are set correctly

### Settings not saving

- Check that the Supabase table was created correctly
- Verify your Supabase credentials are correct
- Check the backend logs for error messages

### Fallback to Environment Variables

If Supabase is not configured or unavailable, the system will automatically use the values from your `.env` file:

- `OPENAI_API_KEY`
- `ELEVENLABS_API_KEY`
- `OPENAI_MODEL`
- `ELEVENLABS_MODEL_ID`

This ensures the application continues to work even if there are database connectivity issues.

## Database Schema

The `admin_settings` table structure:

| Column             | Type      | Description            |
| ------------------ | --------- | ---------------------- |
| id                 | UUID      | Primary key            |
| openai_api_key     | TEXT      | OpenAI API key         |
| elevenlabs_api_key | TEXT      | ElevenLabs API key     |
| openai_model       | TEXT      | OpenAI model name      |
| elevenlabs_model   | TEXT      | ElevenLabs model name  |
| system_prompt      | TEXT      | System prompt template |
| created_at         | TIMESTAMP | Creation timestamp     |
| updated_at         | TIMESTAMP | Last update timestamp  |

The system uses a single row to store all settings. If multiple rows exist, only the first one is used.
