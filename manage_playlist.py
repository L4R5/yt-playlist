#!/usr/bin/env python3
"""
YouTube Playlist Manager - Automated Video Downloader

Monitors a "todo" playlist, downloads videos, and moves them to a "done" playlist.
"""

import os
import sys
import time
import json
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Optional
from threading import Thread

import yt_dlp
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv
from prometheus_client import Counter, Gauge, Histogram, start_http_server


# Load environment variables
load_dotenv()

# Configuration
CLIENT_SECRET_JSON = os.getenv('CLIENT_SECRET_JSON')  # Optional: JSON string of client secret
CREDENTIALS_FILE = os.getenv('CREDENTIALS_FILE', 'client_secret.json')
TOKEN_FILE = os.getenv('TOKEN_FILE', 'token.json')
TODO_PLAYLIST_ID = os.getenv('TODO_PLAYLIST_ID')
DONE_PLAYLIST_ID = os.getenv('DONE_PLAYLIST_ID')
DOWNLOAD_PATH = Path(os.getenv('DOWNLOAD_PATH', './downloads'))
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', 5))
DOWNLOAD_MODE = os.getenv('DOWNLOAD_MODE', 'video').lower()  # 'video' or 'audio'
METRICS_PORT = int(os.getenv('METRICS_PORT', 8080))

# OAuth2 scopes for YouTube API
SCOPES = ['https://www.googleapis.com/auth/youtube']

# YouTube API quota costs (per operation)
QUOTA_COSTS = {
    'playlistItems.list': 1,
    'playlistItems.insert': 50,
    'playlistItems.delete': 50,
}
DAILY_QUOTA_LIMIT = int(os.getenv('DAILY_QUOTA_LIMIT', 10000))

# Prometheus metrics
videos_processed_total = Counter(
    'yt_playlist_videos_processed_total',
    'Total number of videos processed',
    ['status']  # status: success, download_failed, api_failed
)

downloads_total = Counter(
    'yt_playlist_downloads_total',
    'Total number of video downloads attempted',
    ['status']  # status: success, failed
)

api_calls_total = Counter(
    'yt_playlist_api_calls_total',
    'Total number of YouTube API calls',
    ['operation']  # operation: list, insert, delete
)

api_quota_used = Gauge(
    'yt_playlist_api_quota_used',
    'Estimated YouTube API quota units used today'
)

api_quota_remaining = Gauge(
    'yt_playlist_api_quota_remaining',
    'Estimated YouTube API quota units remaining today'
)

playlist_videos_gauge = Gauge(
    'yt_playlist_todo_videos',
    'Current number of videos in TODO playlist'
)

processing_duration_seconds = Histogram(
    'yt_playlist_processing_duration_seconds',
    'Time spent processing videos',
    ['operation']  # operation: download, api_call, full_cycle
)

last_processing_timestamp = Gauge(
    'yt_playlist_last_processing_timestamp',
    'Timestamp of last processing cycle'
)

# Logging setup
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
LOG_FILE = os.getenv('LOG_FILE', '/tmp/playlist_manager.log')

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE)
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"Logging configured: level={LOG_LEVEL}, file={LOG_FILE}")


class QuotaTracker:
    """Track YouTube API quota usage."""
    
    def __init__(self):
        self.used = 0
        self.reset_time = self._get_next_reset_time()
    
    def _get_next_reset_time(self):
        """Get timestamp of next quota reset (midnight Pacific Time)."""
        from datetime import datetime, timedelta
        import pytz
        
        pacific = pytz.timezone('America/Los_Angeles')
        now = datetime.now(pacific)
        tomorrow = now + timedelta(days=1)
        midnight = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        return midnight.timestamp()
    
    def add_usage(self, operation: str):
        """Record API operation and update quota usage."""
        # Check if we need to reset (new day)
        if time.time() >= self.reset_time:
            logger.info("Quota reset - new day started")
            self.used = 0
            self.reset_time = self._get_next_reset_time()
        
        cost = QUOTA_COSTS.get(operation, 0)
        self.used += cost
        
        # Update Prometheus metrics
        api_quota_used.set(self.used)
        api_quota_remaining.set(max(0, DAILY_QUOTA_LIMIT - self.used))
        
        logger.debug(f"Quota: {operation} cost {cost} units (total: {self.used}/{DAILY_QUOTA_LIMIT})")
    
    def get_remaining(self):
        """Get remaining quota units."""
        if time.time() >= self.reset_time:
            return DAILY_QUOTA_LIMIT
        return max(0, DAILY_QUOTA_LIMIT - self.used)


# Global quota tracker
quota_tracker = QuotaTracker()


class PlaylistManager:
    """Manages YouTube playlist operations and video downloads."""
    
    def __init__(self, credentials_file: str, token_file: str, todo_playlist_id: str, done_playlist_id: str):
        """
        Initialize the playlist manager.
        
        Args:
            credentials_file: Path to OAuth2 client credentials JSON file
            token_file: Path to store OAuth2 tokens
            todo_playlist_id: Source playlist with videos to download
            done_playlist_id: Destination playlist for completed downloads
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.todo_playlist_id = todo_playlist_id
        self.done_playlist_id = done_playlist_id
        self.youtube = None
        self._init_youtube_client()
    
    def _get_credentials(self) -> Credentials:
        """Get or create OAuth2 credentials."""
        creds = None
        
        # Load existing token if available
        if os.path.exists(self.token_file):
            logger.info(f"Loading existing credentials from {self.token_file}")
            try:
                creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
            except ValueError as e:
                # Token file exists but missing refresh_token - wait for re-authentication
                if "missing fields refresh_token" in str(e):
                    logger.warning(f"Token file is missing refresh_token: {e}")
                    logger.warning("Waiting for authentication via auth UI...")
                    return None
                raise
        
        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing expired credentials")
                creds.refresh(Request())
            else:
                logger.info("Starting OAuth2 authentication flow")
                
                # Try to load client secret from environment variable first
                if CLIENT_SECRET_JSON:
                    try:
                        logger.info("Loading client secret from CLIENT_SECRET_JSON environment variable")
                        client_config = json.loads(CLIENT_SECRET_JSON)
                        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse CLIENT_SECRET_JSON: {e}")
                        raise ValueError("CLIENT_SECRET_JSON must be valid JSON") from e
                # Fall back to file-based credentials
                elif os.path.exists(self.credentials_file):
                    logger.info(f"Loading client secret from file: {self.credentials_file}")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, SCOPES)
                else:
                    logger.error("No client credentials found")
                    logger.error(f"Either set CLIENT_SECRET_JSON environment variable or")
                    logger.error(f"provide credentials file at: {self.credentials_file}")
                    logger.error("See README.md for instructions")
                    raise FileNotFoundError("Client credentials not found")
                
                creds = flow.run_local_server(port=0)  # Use random available port
                logger.info("Authentication successful!")
            
            # Save credentials for next run
            logger.info(f"Saving credentials to {self.token_file}")
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        return creds
    
    def _init_youtube_client(self) -> None:
        """Initialize YouTube API client with OAuth2."""
        retry_delay = 10  # Start with 10 seconds
        max_delay = 300   # Max 5 minutes between retries
        
        while True:
            try:
                creds = self._get_credentials()
                if creds is None:
                    # Waiting for authentication
                    logger.info(f"Waiting for valid credentials... retrying in {retry_delay} seconds")
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 1.5, max_delay)  # Exponential backoff
                    continue
                
                self.youtube = build('youtube', 'v3', credentials=creds)
                logger.info("YouTube API client initialized successfully with OAuth2")
                return
            except Exception as e:
                logger.error(f"Failed to initialize YouTube API client: {e}")
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.5, max_delay)
    
    def get_playlist_videos(self, playlist_id: str) -> List[Dict[str, str]]:
        """
        Fetch all videos from a playlist.
        
        Args:
            playlist_id: YouTube playlist ID
            
        Returns:
            List of video dictionaries with id, title, and video_id
        """
        videos = []
        next_page_token = None
        
        logger.info(f"Attempting to fetch videos from playlist: {playlist_id}")
        
        try:
            while True:
                request = self.youtube.playlistItems().list(
                    part='snippet',
                    playlistId=playlist_id,
                    maxResults=50,
                    pageToken=next_page_token
                )
                logger.debug(f"Making API request to playlistItems.list with playlistId={playlist_id}")
                
                with processing_duration_seconds.labels(operation='api_call').time():
                    response = request.execute()
                
                # Track API usage
                api_calls_total.labels(operation='list').inc()
                quota_tracker.add_usage('playlistItems.list')
                
                logger.debug(f"API response received. Items count: {len(response.get('items', []))}")
                
                for item in response.get('items', []):
                    videos.append({
                        'playlist_item_id': item['id'],
                        'video_id': item['snippet']['resourceId']['videoId'],
                        'title': item['snippet']['title'],
                        'video_url': f"https://www.youtube.com/watch?v={item['snippet']['resourceId']['videoId']}"
                    })
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
            
            logger.info(f"Retrieved {len(videos)} videos from playlist {playlist_id}")
            playlist_videos_gauge.set(len(videos))
            return videos
            
        except HttpError as e:
            logger.error(f"HTTP error fetching playlist {playlist_id}: {e}")
            logger.error(f"Error status code: {e.resp.status}")
            logger.error(f"Error reason: {e.error_details}")
            if e.resp.status == 404:
                logger.error("Playlist not found. Possible reasons:")
                logger.error("  1. Playlist ID is incorrect")
                logger.error("  2. Playlist is private and API key doesn't have access")
                logger.error("  3. Playlist has been deleted")
                logger.error(f"  Please verify playlist exists: https://www.youtube.com/playlist?list={playlist_id}")
            return []
    
    def download_video(self, video: Dict[str, str], download_path: Path) -> bool:
        """
        Download a video using yt-dlp.
        
        Args:
            video: Video dictionary with url and metadata
            download_path: Directory to save downloaded videos
            
        Returns:
            True if download successful, False otherwise
        """
        # Configure format based on download mode
        if DOWNLOAD_MODE == 'audio':
            format_string = 'bestaudio[ext=m4a]/bestaudio'
            logger.info(f"Download mode: audio-only (original format)")
        else:
            format_string = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            logger.info(f"Download mode: full video")
        
        ydl_opts = {
            'format': format_string,
            'outtmpl': str(download_path / '%(title)s.%(ext)s'),
            'quiet': False,
            'no_warnings': False,
            'ignoreerrors': False,
            'nocheckcertificate': True,
            'retries': 10,
            'fragment_retries': 10,
        }
        
        try:
            logger.info(f"Starting download: {video['title']}")
            downloads_total.labels(status='attempted').inc()
            
            with processing_duration_seconds.labels(operation='download').time():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video['video_url']])
            
            logger.info(f"Successfully downloaded: {video['title']}")
            downloads_total.labels(status='success').inc()
            return True
            
        except Exception as e:
            logger.error(f"Failed to download {video['title']}: {e}")
            downloads_total.labels(status='failed').inc()
            return False
    
    def remove_from_playlist(self, playlist_item_id: str) -> bool:
        """
        Remove a video from a playlist.
        
        Args:
            playlist_item_id: Playlist item ID (not video ID)
            
        Returns:
            True if removal successful, False otherwise
        """
        try:
            self.youtube.playlistItems().delete(id=playlist_item_id).execute()
            
            # Track API usage
            api_calls_total.labels(operation='delete').inc()
            quota_tracker.add_usage('playlistItems.delete')
            
            logger.info(f"Removed playlist item {playlist_item_id}")
            return True
            
        except HttpError as e:
            logger.error(f"Failed to remove playlist item {playlist_item_id}: {e}")
            return False
    
    def add_to_playlist(self, playlist_id: str, video_id: str) -> bool:
        """
        Add a video to a playlist.
        
        Args:
            playlist_id: Target playlist ID
            video_id: YouTube video ID
            
        Returns:
            True if addition successful, False otherwise
        """
        try:
            request_body = {
                'snippet': {
                    'playlistId': playlist_id,
                    'resourceId': {
                        'kind': 'youtube#video',
                        'videoId': video_id
                    }
                }
            }
            
            self.youtube.playlistItems().insert(
                part='snippet',
                body=request_body
            ).execute()
            
            # Track API usage
            api_calls_total.labels(operation='insert').inc()
            quota_tracker.add_usage('playlistItems.insert')
            
            logger.info(f"Added video {video_id} to playlist {playlist_id}")
            return True
            
        except HttpError as e:
            logger.error(f"Failed to add video {video_id} to playlist: {e}")
            return False
    
    def process_video(self, video: Dict[str, str], download_path: Path) -> bool:
        """
        Process a single video: download, remove from todo, add to done.
        
        Args:
            video: Video dictionary with metadata
            download_path: Directory to save downloaded videos
            
        Returns:
            True if entire process successful, False otherwise
        """
        logger.info(f"Processing video: {video['title']}")
        
        # Step 1: Download video
        if not self.download_video(video, download_path):
            return False
        
        # Step 2: Add to done playlist
        if not self.add_to_playlist(self.done_playlist_id, video['video_id']):
            logger.warning(f"Downloaded but failed to add to done playlist: {video['title']}")
            videos_processed_total.labels(status='api_failed').inc()
            # Continue anyway - video is downloaded
        
        # Step 3: Remove from todo playlist
        if not self.remove_from_playlist(video['playlist_item_id']):
            logger.warning(f"Downloaded but failed to remove from todo playlist: {video['title']}")
            videos_processed_total.labels(status='api_failed').inc()
            return False
        
        logger.info(f"Successfully processed: {video['title']}")
        videos_processed_total.labels(status='success').inc()
        return True
    
    def run_once(self, download_path: Path) -> None:
        """
        Process all videos in the todo playlist once.
        
        Args:
            download_path: Directory to save downloaded videos
        """
        logger.info("="*60)
        logger.info("Starting playlist processing cycle")
        logger.info(f"TODO Playlist ID: {self.todo_playlist_id}")
        logger.info(f"DONE Playlist ID: {self.done_playlist_id}")
        logger.info(f"Download Path: {download_path}")
        logger.info(f"API Quota Used: {quota_tracker.used}/{DAILY_QUOTA_LIMIT} ({quota_tracker.get_remaining()} remaining)")
        logger.info("="*60)
        
        cycle_start = time.time()
        
        # Ensure download directory exists
        download_path.mkdir(parents=True, exist_ok=True)
        
        # Fetch videos from todo playlist
        videos = self.get_playlist_videos(self.todo_playlist_id)
        
        if not videos:
            logger.info("No videos in todo playlist")
            last_processing_timestamp.set(time.time())
            return
        
        logger.info(f"Found {len(videos)} videos to process")
        
        # Process each video
        for video in videos:
            try:
                with processing_duration_seconds.labels(operation='full_cycle').time():
                    success = self.process_video(video, download_path)
                    if not success:
                        videos_processed_total.labels(status='download_failed').inc()
            except Exception as e:
                logger.error(f"Unexpected error processing {video['title']}: {e}")
                videos_processed_total.labels(status='download_failed').inc()
                # Continue with next video
        
        cycle_duration = time.time() - cycle_start
        logger.info(f"Playlist processing cycle complete (took {cycle_duration:.1f}s)")
        logger.info(f"API Quota Used: {quota_tracker.used}/{DAILY_QUOTA_LIMIT} ({quota_tracker.get_remaining()} remaining)")
        last_processing_timestamp.set(time.time())
    
    def run_daemon(self, download_path: Path, poll_interval: int) -> None:
        """
        Run continuously, checking for new videos periodically.
        
        Args:
            download_path: Directory to save downloaded videos
            poll_interval: Seconds between checks
        """
        logger.info(f"Starting daemon mode (checking every {poll_interval} seconds)")
        
        try:
            while True:
                self.run_once(download_path)
                logger.info(f"Sleeping for {poll_interval} seconds...")
                time.sleep(poll_interval)
                
        except KeyboardInterrupt:
            logger.info("Daemon stopped by user")
        except Exception as e:
            logger.error(f"Daemon encountered fatal error: {e}")
            raise


def validate_config() -> bool:
    """
    Validate required configuration is present.
    
    Returns:
        True if configuration valid, False otherwise
    """
    errors = []
    
    logger.info("Validating configuration...")
    
    # Check for either CLIENT_SECRET_JSON or credentials file
    if CLIENT_SECRET_JSON:
        logger.info(f"✓ CLIENT_SECRET_JSON environment variable set")
        try:
            json.loads(CLIENT_SECRET_JSON)
            logger.info(f"✓ CLIENT_SECRET_JSON is valid JSON")
        except json.JSONDecodeError:
            errors.append("CLIENT_SECRET_JSON is not valid JSON")
            logger.error(f"✗ CLIENT_SECRET_JSON contains invalid JSON")
    elif os.path.exists(CREDENTIALS_FILE):
        logger.info(f"✓ Credentials file found: {CREDENTIALS_FILE}")
    else:
        errors.append(f"No client credentials found (neither CLIENT_SECRET_JSON nor {CREDENTIALS_FILE})")
        logger.error(f"✗ No client credentials found")
        logger.error(f"  Either set CLIENT_SECRET_JSON env var or provide {CREDENTIALS_FILE}")
    
    if not TODO_PLAYLIST_ID:
        errors.append("TODO_PLAYLIST_ID not set")
    else:
        logger.info(f"✓ TODO_PLAYLIST_ID: {TODO_PLAYLIST_ID}")
    
    if not DONE_PLAYLIST_ID:
        errors.append("DONE_PLAYLIST_ID not set")
    else:
        logger.info(f"✓ DONE_PLAYLIST_ID: {DONE_PLAYLIST_ID}")
    
    if errors:
        logger.error("Configuration errors:")
        for error in errors:
            logger.error(f"  - {error}")
        logger.error("\nPlease fix these issues. See README.md for setup instructions")
        return False
    
    logger.info("Configuration valid!")
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='YouTube Playlist Manager - Automated Video Downloader'
    )
    parser.add_argument(
        '--daemon',
        action='store_true',
        help='Run continuously in daemon mode'
    )
    parser.add_argument(
        '--download-path',
        type=Path,
        default=DOWNLOAD_PATH,
        help=f'Download directory (default: {DOWNLOAD_PATH})'
    )
    parser.add_argument(
        '--poll-interval',
        type=int,
        default=POLL_INTERVAL,
        help=f'Seconds between checks in daemon mode (default: {POLL_INTERVAL})'
    )
    parser.add_argument(
        '--metrics-port',
        type=int,
        default=METRICS_PORT,
        help=f'Port for Prometheus metrics endpoint (default: {METRICS_PORT})'
    )
    
    args = parser.parse_args()
    
    # Start Prometheus metrics server
    try:
        start_http_server(args.metrics_port)
        logger.info(f"Prometheus metrics server started on port {args.metrics_port}")
        logger.info(f"Metrics available at http://localhost:{args.metrics_port}/metrics")
    except OSError as e:
        logger.warning(f"Could not start metrics server on port {args.metrics_port}: {e}")
        logger.warning("Continuing without metrics endpoint")
    
    # Validate configuration
    if not validate_config():
        sys.exit(1)
    
    # Initialize playlist manager
    try:
        manager = PlaylistManager(
            credentials_file=CREDENTIALS_FILE,
            token_file=TOKEN_FILE,
            todo_playlist_id=TODO_PLAYLIST_ID,
            done_playlist_id=DONE_PLAYLIST_ID
        )
    except Exception as e:
        logger.error(f"Failed to initialize playlist manager: {e}")
        sys.exit(1)
    
    # Run
    if args.daemon:
        manager.run_daemon(args.download_path, args.poll_interval)
    else:
        manager.run_once(args.download_path)


if __name__ == '__main__':
    main()
