# YouTube Playlist Manager

Automated video downloader that monitors a YouTube "todo" playlist, downloads videos, and moves them to a "done" playlist for visibility.

> **Note:** This project was created 100% by AI (GitHub Copilot & Claude), demonstrating AI-assisted software development capabilities.

## Features

- 🎥 Automatically downloads videos from a monitored playlist
- 📋 Moves completed videos from "todo" to "done" playlist
- 🔄 Runs continuously in daemon mode or as a one-time job
- 🛡️ Graceful error handling with retry logic
- 📝 Detailed logging for monitoring
- ⚙️ Configurable via environment variables

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up OAuth2 Credentials

**Why OAuth2?** Unlike API keys, OAuth2 allows the application to modify your playlists (add/remove videos).

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable "YouTube Data API v3"
4. Go to **"APIs & Services"** → **"Credentials"**
5. Click **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**
6. If prompted, configure the OAuth consent screen:
   - User Type: **External**
   - App name: `YouTube Playlist Manager`
   - Add your email as test user
7. Application type: **Desktop app**
8. Name it (e.g., "Playlist Manager Client")
9. Download the JSON file
10. **Choose one of these methods:**
    - **Method A (File)**: Save it as `client_secret.json` in the project directory
    - **Method B (Environment Variable)**: Copy the JSON content to use as `CLIENT_SECRET_JSON` (see step 4)

### 3. Get Playlist IDs

From your YouTube playlist URLs:
- URL format: `https://www.youtube.com/playlist?list=PLxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- The `PLxxxxxxxxxxxxxxxxxxxxxxxxxxxx` part is your playlist ID

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env with your playlist IDs (credentials file is already set)
```

Example `.env`:
```bash
# OAuth2 credentials - use ONE of these methods:
# Method A: File path (traditional)
CREDENTIALS_FILE=client_secret.json

# Method B: JSON string (useful for Docker/CI/CD)
# CLIENT_SECRET_JSON={"installed":{"client_id":"...","client_secret":"...","redirect_uris":["http://localhost"]}}

# Required: Your playlist IDs
TODO_PLAYLIST_ID=PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DONE_PLAYLIST_ID=PLyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy

# Optional: Download configuration
DOWNLOAD_PATH=./downloads
POLL_INTERVAL=300
DOWNLOAD_MODE=video  # Options: 'video' or 'audio'
```

**Using CLIENT_SECRET_JSON**: Copy the entire JSON content from your downloaded credentials file and set it as a single-line environment variable (escape quotes if needed for your shell).

### Download Modes

- **`video`** (default): Downloads full video with best quality video and audio
- **`audio`**: Downloads audio-only in original format (typically M4A)

### 5. First Run - Authenticate

On first run, the application will open a browser window for OAuth2 authentication:

```bash
python manage_playlist.py
```

1. Browser will open automatically
2. Sign in to your Google account
3. Grant permissions to manage YouTube playlists
4. Authentication complete! Token saved to `token.json`
5. Subsequent runs won't require re-authentication

## Usage

### Run Once (Process Current Queue)

```bash
python manage_playlist.py
```

### Run as Daemon (Continuous Monitoring)

```bash
python manage_playlist.py --daemon
```

### Custom Options

```bash
# Custom download path
python manage_playlist.py --download-path /path/to/videos

# Custom poll interval (seconds)
python manage_playlist.py --daemon --poll-interval 600

# Custom metrics port
python manage_playlist.py --metrics-port 9090

# Combine options
python manage_playlist.py --daemon --download-path ./my-videos --poll-interval 120
```

## Monitoring

The application exposes Prometheus metrics on port 8080 (configurable with `--metrics-port`):

```bash
# View metrics
curl http://localhost:8080/metrics
```

**Available metrics:**
- `yt_playlist_videos_processed_total` - Videos processed by status
- `yt_playlist_downloads_total` - Download success/failure counts
- `yt_playlist_api_calls_total` - YouTube API call counts by operation
- `yt_playlist_api_quota_used` - Estimated API quota used today
- `yt_playlist_api_quota_remaining` - Estimated remaining quota
- `yt_playlist_todo_videos` - Current size of TODO playlist
- `yt_playlist_processing_duration_seconds` - Operation timing histograms

Metrics are compatible with Prometheus, Grafana, and other monitoring tools.

## How It Works

1. **Monitor**: Fetches videos from the "todo" playlist
2. **Download**: Downloads each video using yt-dlp
3. **Move**: On success:
   - Adds video to "done" playlist
   - Removes video from "todo" playlist
4. **Repeat**: In daemon mode, waits and checks again

## API Quota Considerations

YouTube Data API v3 has a daily quota limit (10,000 units by default):
- List playlist items: 1 unit per request
- Insert playlist item: 50 units
- Delete playlist item: 50 units
- **Each video costs ~101 units** (list + insert + delete)

With default quota, you can process ~99 videos per day.

## Deployment

### Docker (Recommended)

**Prerequisites:**
- Docker and Docker Compose installed
- OAuth2 credentials already set up (see Setup section above)

**Option A: Use Pre-built Image from GitHub Container Registry**

```bash
# Pull the latest image
docker pull ghcr.io/l4r5/yt-playlist:latest

# Use 'ghcr.io/l4r5/yt-playlist:latest' instead of 'yt-playlist' in commands below
```

**Option B: Build Locally**

**Steps:**

1. **Create data directory and copy credentials:**
```bash
mkdir -p data downloads
cp client_secret.json data/
# token.json will be created during first authentication
```

2. **Set environment variables:**
```bash
# Add to .env file
echo "TODO_PLAYLIST_ID=PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" >> .env
echo "DONE_PLAYLIST_ID=PLyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy" >> .env
```

3. **Build the image (if building locally):**
```bash
docker build -t yt-playlist .
```

4. **Run:**
```bash
# Build the image
docker-compose build

# First run - authenticate (interactive mode, port forwarding enabled)
docker-compose run --rm --service-ports yt-playlist
# Browser will open for OAuth - grant permissions

# After authentication, run as daemon
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

**Manual Docker commands:**
```bash
# Build
docker build -t yt-playlist .

# Or use pre-built image
docker pull ghcr.io/l4r5/yt-playlist:latest

# Method A: Using CLIENT_SECRET_JSON (no file needed)
docker run --rm -it \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/downloads:/app/downloads \
  -e CLIENT_SECRET_JSON='{"installed":{"client_id":"...","client_secret":"...","redirect_uris":["http://localhost"]}}' \
  -e TODO_PLAYLIST_ID=PLxxxx \
  -e DONE_PLAYLIST_ID=PLyyyy \
  yt-playlist

# Method B: Using file mount (requires client_secret.json in ./data/)
docker run --rm -it \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/downloads:/app/downloads \
  -e TODO_PLAYLIST_ID=PLxxxx \
  -e DONE_PLAYLIST_ID=PLyyyy \
  yt-playlist

# Run as daemon (after authentication, add --daemon)
docker run -d \
  --name youtube-playlist-manager \
  --restart unless-stopped \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/downloads:/app/downloads \
  -e CLIENT_SECRET_JSON='{"installed":{...}}' \
  -e TODO_PLAYLIST_ID=PLxxxx \
  -e DONE_PLAYLIST_ID=PLyyyy \
  yt-playlist --daemon
```

### Run in Background (Linux/macOS)

```bash
nohup python manage_playlist.py --daemon > output.log 2>&1 &
```

### Systemd Service (Linux)

Create `/etc/systemd/system/youtube-playlist.service`:

```ini
[Unit]
Description=YouTube Playlist Manager
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/yt-playlist
ExecStart=/usr/bin/python3 manage_playlist.py --daemon
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable youtube-playlist
sudo systemctl start youtube-playlist
sudo systemctl status youtube-playlist
```

## Logging

Logs are written to:
- Console (stdout)
- `playlist_manager.log` file

## Troubleshooting

### Authentication Errors
- Verify `client_secret.json` is in the project directory
- Check OAuth consent screen is configured in Google Cloud Console
- Ensure your Google account is added as a test user
- Delete `token.json` and re-authenticate if token is corrupted

### Playlist Not Found
- Verify playlist IDs are correct (check URLs)
- Ensure playlists are public/unlisted or owned by authenticated account

### Download Failures
- Check internet connection
- Video may be private/deleted
- yt-dlp may need updating: `pip install -U yt-dlp`

### API Quota Exceeded
- Check quota usage in Google Cloud Console
- Wait for quota reset (midnight Pacific Time)
- Request quota increase if needed

## License

MIT
