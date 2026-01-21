# YouTube Playlist Manager - AI Coding Instructions

## Project Overview
Automated video downloader that monitors a YouTube "todo" playlist, downloads videos, and moves them to a "done" playlist for visibility. Runs continuously in the background.

## Architecture & Components

### Core Module
- **manage_playlist.py**: Main automation script
  - Monitors "todo" playlist for new videos
  - Downloads videos using yt-dlp
  - Moves completed videos from "todo" → "done" playlist
  - Handles failures gracefully (retry logic, error logging)

## Development Conventions

### Python Style
- Follow PEP 8 style guidelines
- Use type hints for function signatures
- Document functions with docstrings (Google or NumPy style)

### Error Handling
- Handle YouTube API rate limits gracefully
- Implement retry logic for transient failures
- Provide clear error messages for authentication issues

### Configuration
- Store OAuth2 credentials securely (never commit)
- `client_secret.json`: OAuth2 client credentials from Google Cloud Console
- `token.json`: Auto-generated OAuth2 tokens (created on first authentication)
- Use `.env` file for local development (add to `.gitignore`)
- Required env vars:
  - `CREDENTIALS_FILE`: Path to OAuth2 client secret (default: `client_secret.json`)
  - `TOKEN_FILE`: Path to store OAuth tokens (default: `token.json`)
  - `TODO_PLAYLIST_ID`: Source playlist with videos to download
  - `DONE_PLAYLIST_ID`: Destination playlist for completed downloads
  - `DOWNLOAD_PATH`: Directory for saved videos (optional, default: `./downloads`)
  - `POLL_INTERVAL`: Seconds between checks (optional, default: 300)
  - `DOWNLOAD_MODE`: Download type - `video` (full video, default) or `audio` (audio-only, original format)

## Key Workflows

### Setup
```bash
# Install dependencies
pip install google-api-python-client google-auth google-auth-oauthlib yt-dlp python-dotenv

# Configure environment
cp .env.example .env  # Edit with your playlist IDs

# Download OAuth2 credentials from Google Cloud Console
# Save as client_secret.json

# First run - authenticate (opens browser)
python manage_playlist.py
```

### Running
```bash
# Run once (process current todo playlist)
python manage_playlist.py

# Run continuously (monitor and auto-download)
python manage_playlist.py --daemon
```

### Download Process Flow
1. Fetch all videos from TODO_PLAYLIST_ID
2. For each video:
   - Download using yt-dlp to DOWNLOAD_PATH
   - On success: Remove from todo playlist, add to done playlist
   - On failure: Log error, keep in todo playlist (retry next cycle)
3. Sleep for POLL_INTERVAL, repeat

## External Dependencies

### Required Libraries
- `google-api-python-client`: YouTube Data API v3 client for playlist manipulation
- `google-auth`: Authentication handling
- `google-auth-oauthlib`: OAuth2 flow for user authentication
- `yt-dlp`: Video downloading (preferred over youtube-dl)
- `python-dotenv`: Environment variable management

### API Considerations
- YouTube Data API v3 has quota limits (10,000 units/day by default)
- Playlist item operations:
  - `playlistItems.list()`: 1 unit per request
  - `playlistItems.insert()`: 50 units (adding to done playlist)
  - `playlistItems.delete()`: 50 units (removing from todo playlist)
- Each processed video costs ~101 units (list + insert + delete)
- Cache playlist data to minimize redundant API calls

### yt-dlp Usage
```python
import yt_dlp

# Full video download
ydl_opts = {
    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    'outtmpl': '%(title)s.%(ext)s',
    'quiet': False,
    'no_warnings': False,
}

# Audio-only download (original format, typically M4A)
ydl_opts_audio = {
    'format': 'bestaudio[ext=m4a]/bestaudio',
    'outtmpl': '%(title)s.%(ext)s',
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([video_url])
```

## Code Patterns

### API Client Initialization
```python
from googleapiclient.discovery import build

youtube = build('youtube', 'v3', developerKey=API_KEY)
```

### Playlist Operations
- Use `playlists().list()` to fetch playlist metadata
- Use `playlistItems().list()` to get videos in a playlist
- Implement pagination for playlists with >50 videos (maxResults=50)

## Testing Strategy
- Mock YouTube API responses for unit tests
- Use pytest as the testing framework
- Test error scenarios (invalid API key, non-existent playlist)
- Mock yt-dlp downloads to avoid actual video downloads in tests

## Future Enhancements to Consider
- CLI argument parsing with `argparse` or `click`
- Logging configuration for debugging API interactions and downloads
- Systemd service file or Docker container for deployment
- Progress notifications (email, webhook, Discord bot)
- Download quality selection and format preferences
- Concurrent downloads with rate limiting
