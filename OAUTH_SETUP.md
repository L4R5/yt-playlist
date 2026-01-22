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
   
   **Choose application type based on your deployment:**
   
   **Option A: Desktop app** (for CLI/local usage only)
   - Application type: **Desktop app**
   - Name: "Playlist Manager Desktop Client"
   - Click "Create"
   - Note: Desktop apps have fixed redirect URIs (`http://localhost`, `urn:ietf:wg:oauth:2.0:oob`)
   - Cannot add custom redirect URIs
   - ✅ Works for: CLI usage, local development
   - ❌ Does NOT work for: Kubernetes auth UI with ingress
   
   **Option B: Web application** (recommended for Kubernetes/Ingress)
   - Application type: **Web application**
   - Name: "Playlist Manager Web Client"
   - Under "Authorized redirect URIs", click "ADD URI" and add:
     - `http://localhost` (for local/CLI usage)
     - `http://localhost:5000/callback` (for auth UI with port-forward)
     - `https://auth.example.com/callback` (replace with your actual ingress domain)
   - Click "Create"
   - ✅ Works for: Everything (CLI, port-forward, ingress)
   
   **Recommendation:** Use **Web application** type for maximum flexibility, especially if planning to use Kubernetes auth UI with ingress.

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

### "Error 400: redirect_uri_mismatch"

**Problem:** Google OAuth is rejecting the redirect URI.

**Root cause:** You're likely using a Desktop app OAuth client, which has fixed redirect URIs and cannot be customized.

**Solution:**

**If using Desktop app type:**
- Desktop app clients only support `http://localhost` (any port) and `urn:ietf:wg:oauth:2.0:oob`
- This works for CLI usage but NOT for auth UI with custom ingress domains
- If you need custom redirect URIs, create a new Web application OAuth client (see below)

**If using Web application type:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **"APIs & Services"** → **"Credentials"**
3. Click on your **Web application** OAuth client name
4. Scroll down to **"Authorized redirect URIs"** section
5. Click **"ADD URI"** and add the redirect URI that matches your deployment:
   - `http://localhost` (for CLI usage)
   - `http://localhost:5000/callback` (for auth UI with port-forward)
   - `https://your-domain.com/callback` (for auth UI with ingress)
6. Click **"SAVE"**
7. **Wait 5 minutes** for changes to propagate
8. Try authenticating again

**Create new Web application OAuth client:**
1. Go to "APIs & Services" → "Credentials"
2. Click "+ CREATE CREDENTIALS" → "OAuth client ID"
3. Application type: **Web application**
4. Name: "Playlist Manager Web Client"
5. Add redirect URIs as needed
6. Download the new credentials
7. Replace your old `client_secret.json` with the new one

### "Access blocked: This app's request is invalid"
- Make sure you added your email as a test user in OAuth consent screen
- Check that YouTube Data API v3 is enabled

### "Credentials file not found"
- Make sure `client_secret.json` is in the project root directory
- Check the filename matches exactly (case-sensitive)

### "Token expired" errors
- Delete `token.json` and run again to re-authenticate
- The app will automatically refresh tokens normally
