#!/usr/bin/env python3
"""
OAuth2 Authentication Web UI for YouTube Playlist Manager

Simple web interface for completing OAuth2 authentication and storing
tokens in persistent storage.
"""

import os
import json
import logging
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.middleware.proxy_fix import ProxyFix
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials

# Configuration
CLIENT_SECRET_JSON = os.getenv('CLIENT_SECRET_JSON')
CREDENTIALS_FILE = os.getenv('CREDENTIALS_FILE', '/config/client_secret.json')
SCOPES = ['https://www.googleapis.com/auth/youtube']
PORT = int(os.getenv('PORT', 5000))
REDIRECT_URI = os.getenv('REDIRECT_URI', None)  # Optional: explicit redirect URI for ingress

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Trust proxy headers (X-Forwarded-Proto, X-Forwarded-Host) from ingress
# This allows Flask to correctly detect HTTPS when behind a reverse proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_client_config():
    """Get OAuth2 client configuration from env var or file."""
    if CLIENT_SECRET_JSON:
        try:
            return json.loads(CLIENT_SECRET_JSON)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse CLIENT_SECRET_JSON: {e}")
            raise
    elif os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, 'r') as f:
            return json.load(f)
    else:
        raise FileNotFoundError("No client credentials found")


def save_token_to_file(token_json: str):
    """Save OAuth token to persistent file."""
    try:
        token_file = '/app/data/token.json'
        with open(token_file, 'w') as f:
            f.write(token_json)
        logger.info(f"Saved token to {token_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to save token to Kubernetes: {e}")
        return False


@app.route('/')
def index():
    """Main page with authentication button."""
    authenticated = session.get('authenticated', False)
    error = session.pop('error', None)
    return render_template('index.html', authenticated=authenticated, error=error)


@app.route('/auth')
def auth():
    """Start OAuth2 flow."""
    try:
        client_config = get_client_config()
        
        # Use explicit redirect URI if set (for ingress), otherwise auto-detect
        redirect_uri = REDIRECT_URI or url_for('callback', _external=True)
        logger.info(f"Using redirect URI: {redirect_uri}")
        
        # Create flow with redirect URI
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'  # Force consent screen to always get refresh_token
        )
        
        session['state'] = state
        return redirect(authorization_url)
    
    except Exception as e:
        logger.error(f"Error starting OAuth flow: {e}")
        session['error'] = str(e)
        return redirect(url_for('index'))


@app.route('/callback')
def callback():
    """OAuth2 callback handler."""
    try:
        # Verify state
        state = session.get('state')
        if not state or state != request.args.get('state'):
            raise ValueError("Invalid state parameter")
        
        client_config = get_client_config()
        
        # Use explicit redirect URI if set (for ingress), otherwise auto-detect
        redirect_uri = REDIRECT_URI or url_for('callback', _external=True)
        
        # Complete the flow
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            state=state,
            redirect_uri=redirect_uri
        )
        
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        
        # Save token to persistent file
        token_json = credentials.to_json()
        
        if save_token_to_file(token_json):
            session['authenticated'] = True
            logger.info("Successfully authenticated and saved token")
            return redirect(url_for('success'))
        else:
            raise Exception("Failed to save token to file")
    
    except Exception as e:
        logger.error(f"Error in OAuth callback: {e}")
        session['error'] = str(e)
        return redirect(url_for('index'))


@app.route('/success')
def success():
    """Success page after authentication."""
    return render_template('success.html', token_file='/app/data/token.json')


@app.route('/health')
def health():
    """Health check endpoint."""
    return {'status': 'healthy'}, 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)
