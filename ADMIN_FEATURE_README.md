# Admin Dashboard - Meditation Storage & Management

This document describes the admin dashboard feature where every meditation created by users is stored, listed, viewable, and downloadable.

## Overview

The meditation app now has two distinct sides:

1. **User Side**: Create and listen to meditations
2. **Admin Side**: Manage all meditations, view, and download them

## Features Implemented

### 1. Meditation Storage

- After creating a meditation, it is automatically stored in Supabase database
- Audio files are uploaded to Supabase Storage
- Meditation metadata is stored including:
  - Disease and symptom
  - Additional instructions
  - Full meditation text
  - Audio URL
  - Duration
  - Creation timestamp

### 2. Admin Meditations Dashboard

- List all created meditations
- View meditation details (text, metadata)
- Download audio files
- Delete meditations
- Listen to audio directly in the browser

## Database Schema

### Meditations Table

```sql
CREATE TABLE meditations (
    id UUID PRIMARY KEY,
    session_id TEXT UNIQUE NOT NULL,
    disease TEXT NOT NULL,
    symptom TEXT NOT NULL,
    additional_instructions TEXT,
    meditation_text TEXT NOT NULL,
    audio_url TEXT,
    duration_seconds INTEGER,
    status TEXT NOT NULL DEFAULT 'completed',
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

## API Endpoints

### Admin Endpoints

#### List All Meditations

```
GET /api/admin/meditations?limit=100&offset=0
```

Returns a list of all meditations with pagination support.

#### Get Meditation Details

```
GET /api/admin/meditations/{meditation_id}
```

Returns detailed information about a specific meditation.

#### Delete Meditation

```
DELETE /api/admin/meditations/{meditation_id}
```

Deletes a meditation from the database and storage.

## Supabase Storage

### Bucket Configuration

- **Bucket Name**: `meditation-audio`
- **Public Access**: Yes (to allow direct audio streaming)
- **File Size Limit**: 100MB
- **Storage Path**: `meditations/{session_id}.mp3`

## Frontend Pages

### Admin Settings Page

- Location: `/admin`
- Manages API settings and configuration
- Now includes a "View Meditations" button

### Admin Meditations Page

- Location: `/admin/meditations`
- Lists all created meditations
- Features:
  - List view with meditation metadata
  - View button to see full details
  - Download button for audio files
  - Delete button to remove meditations
  - In-browser audio player

## Setup Instructions

### 1. Run Database Migration

Execute the SQL migration to create the meditations table:

```bash
# In your Supabase dashboard SQL editor, run:
# backend/supabase_migration_meditations.sql
```

### 2. Configure Supabase Storage

1. Go to your Supabase dashboard
2. Navigate to Storage
3. Create a new bucket named `meditation-audio`
4. Make it public (to allow direct audio access)
5. Set file size limit to 100MB

Alternatively, the bucket will be created automatically on first upload.

### 3. Environment Variables

Ensure your `.env` file has the correct Supabase credentials:

```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
```

### 4. Install Frontend Dependencies

If using `date-fns` for date formatting:

```bash
cd frontend
npm install date-fns
# or
pnpm add date-fns
```

## Usage

### For Users

1. Navigate to the create page
2. Fill in disease, symptom, and additional instructions
3. Generate meditation
4. Meditation is automatically saved to the database

### For Admins

1. Navigate to `/admin`
2. Click "View Meditations" button
3. See all created meditations
4. Use actions to:
   - View meditation details
   - Download audio files
   - Delete meditations

## Features by Side

### User Side

- Create meditation
- Listen to generated meditation
- Download their own meditation

### Admin Side

- View all meditations created by all users
- Download any meditation
- Delete any meditation
- View meditation text and metadata
- Listen to audio in browser

## Security Considerations

- Admin endpoints should be protected with authentication
- Consider adding role-based access control
- Implement rate limiting on download endpoints
- Consider adding file size limits on uploads

## Future Enhancements

- Add search and filtering
- Add pagination on frontend
- Add user authentication and user-specific meditation storage
- Add export functionality (CSV, JSON)
- Add analytics dashboard
- Add email notifications for new meditations
