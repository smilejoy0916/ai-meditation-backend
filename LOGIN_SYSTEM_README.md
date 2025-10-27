# Login System - User & Admin Separation

## Overview

The application now has a complete separation between user and admin authentication, with distinct login flows and access controls.

## Features

### 1. Dual Login System

- **User Login**: For creating and listening to meditations
- **Admin Login**: For managing settings, viewing all meditations, and downloading content

### 2. Separate Passwords

- Users have their own password (default: `user`)
- Admins have a separate password (default: `admin`)
- Both can be configured via environment variables

### 3. Role-Based Access Control

- **User Role**: Can only access the meditation creation and listening features
- **Admin Role**: Can access admin dashboard, manage settings, and view all meditations

## Environment Variables

Add these to your `.env` file:

```env
# User login password (default: "user")
USER_PASSWORD=user

# Admin login password (default: "admin")
ADMIN_PASSWORD=admin
```

## User Flow

### User Login

1. Visit the login page
2. Select "User" role
3. Enter user password
4. Redirected to `/create` to generate meditations
5. Can create and listen to meditations

### Admin Login

1. Visit the login page
2. Select "Admin" role
3. Enter admin password
4. Redirected to `/admin` settings page
5. Can:
   - Manage API keys and settings
   - View all meditations
   - Download meditation audio files
   - Delete meditations

## Security Features

### Backend Protection

- All admin endpoints require password authentication
- Password is verified on each admin API call
- User routes are separate from admin routes

### Frontend Protection

- Role-based page access
- Users cannot access admin pages
- Admins cannot access user pages
- Session-based authentication with role storage

## API Endpoints

### User Endpoints (No password required)

- `POST /api/auth` - Authenticate with role selection
- `POST /api/generate` - Create meditation
- `GET /api/status` - Check generation status
- `GET /api/audio` - Stream audio file

### Admin Endpoints (Require admin password)

- `GET /api/admin/settings?password=...` - Get settings
- `PUT /api/admin/settings?password=...` - Update settings
- `GET /api/admin/meditations?password=...` - List meditations
- `GET /api/admin/meditations/{id}?password=...` - Get meditation details
- `DELETE /api/admin/meditations/{id}?password=...` - Delete meditation

## Frontend Routes

### User Routes

- `/` - Login page (selects user or admin)
- `/create` - Create meditation page (user only)
- `/processing` - Processing page (user only)
- `/listen` - Listen to meditation (user only)

### Admin Routes

- `/admin` - Admin settings page (admin only)
- `/admin/meditations` - Meditations management page (admin only)

## Implementation Details

### Session Storage

```javascript
sessionStorage.setItem("authenticated", "true");
sessionStorage.setItem("role", "user" | "admin");
sessionStorage.setItem("password", "password");
```

### Role Checks

Each protected page checks:

```javascript
const role = sessionStorage.getItem("role");
if (role !== "admin") {
  router.push("/");
}
```

## Default Passwords

**Development:**

- User: `user`
- Admin: `admin`

**Production:**
Change these passwords in your environment variables!

## Usage

### For Users

1. Login as "User" with user password
2. Create meditation by filling in the form
3. Listen to generated meditation
4. Logout when done

### For Admins

1. Login as "Admin" with admin password
2. Manage API keys and ElevenLabs voice settings
3. View all meditations created by users
4. Download or delete meditations
5. Logout when done

## Notes

- Passwords are case-sensitive
- Session is stored in browser sessionStorage
- Logout clears all session data
- Both login types start from the same page (`/`)
- Role selection is done before password entry
