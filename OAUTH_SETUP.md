# OAuth2 Setup Guide

## Quick Steps to Get client_secret.json

1. **Go to Google Cloud Console**
   - Visit: https://console.cloud.google.com/

2. **Create/Select Project**
   - Click project dropdown at top
   - Click "New Project" (or select existing)
   - Name: "YouTube Playlist Manager"
   - Click "Create"

3. **Enable YouTube Data API v3**
   - Go to "APIs & Services" → "Library" (left menu)
   - Search: "YouTube Data API v3"
   - Click it → Click "Enable"

4. **Configure OAuth Consent Screen** (First time only)
   - Go to "APIs & Services" → "OAuth consent screen"
   - User Type: Select "External" → Click "Create"
   - App information:
     - App name: `YouTube Playlist Manager`
     - User support email: (your email)
     - Developer contact: (your email)
   - Click "Save and Continue"
   - Scopes: Click "Save and Continue" (no changes needed)
   - Test users: Click "Add Users"
     - Add your Google email
   - Click "Save and Continue"
   - Click "Back to Dashboard"

5. **Create OAuth Client ID**
   - Go to "APIs & Services" → "Credentials"
   - Click "+ CREATE CREDENTIALS" at top
   - Select "OAuth client ID"
   - Application type: **Desktop app**
   - Name: "Playlist Manager Desktop Client"
   - Click "Create"

6. **Download Credentials**
   - Click the download icon (⬇️) next to your newly created OAuth client
   - Save the file as `client_secret.json` in your project directory
   - **Important:** Keep this file private!

7. **Update .env file**
   ```bash
   cp .env.example .env
   # Edit .env and set your playlist IDs
   ```

8. **Run the application**
   ```bash
   python manage_playlist.py
   ```
   - Browser will open automatically
   - Sign in with your Google account
   - Click "Allow" to grant permissions
   - Done! Token saved to `token.json`

## Troubleshooting

### "Access blocked: This app's request is invalid"
- Make sure you added your email as a test user in OAuth consent screen
- Check that YouTube Data API v3 is enabled

### "Credentials file not found"
- Make sure `client_secret.json` is in the project root directory
- Check the filename matches exactly (case-sensitive)

### "Token expired" errors
- Delete `token.json` and run again to re-authenticate
- The app will automatically refresh tokens normally
