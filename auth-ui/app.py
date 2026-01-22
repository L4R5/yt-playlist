#!/usr/bin/env python3
"""
OAuth2 Authentication Web UI for YouTube Playlist Manager

Simple web interface for completing OAuth2 authentication and storing
tokens in Kubernetes secrets.
"""

import os
import json
import logging
from flask import Flask, render_template, request, redirect, url_for, session
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from kubernetes import client, config

# Configuration
CLIENT_SECRET_JSON = os.getenv('CLIENT_SECRET_JSON')
CREDENTIALS_FILE = os.getenv('CREDENTIALS_FILE', '/config/client_secret.json')
SECRET_NAME = os.getenv('SECRET_NAME', 'yt-playlist-credentials')
NAMESPACE = os.getenv('NAMESPACE', 'default')
SCOPES = ['https://www.googleapis.com/auth/youtube']
PORT = int(os.getenv('PORT', 5000))
REDIRECT_URI = os.getenv('REDIRECT_URI', None)  # Optional: explicit redirect URI for ingress

app = Flask(__name__)
app.secret_key = os.urandom(24)

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


def save_token_to_kubernetes(token_json: str):
    """Save OAuth token to Kubernetes secret."""
    try:
        # Load Kubernetes config (in-cluster or kubeconfig)
        try:
            config.load_incluster_config()
            logger.info("Using in-cluster Kubernetes config")
        except config.ConfigException:
            config.load_kube_config()
            logger.info("Using local kubeconfig")
        
        v1 = client.CoreV1Api()
        
        # Get client secret for the secret
        client_config = get_client_config()
        client_secret_str = json.dumps(client_config)
        
        # Create or update secret
        secret = client.V1Secret(
            metadata=client.V1ObjectMeta(name=SECRET_NAME),
            string_data={
                'CLIENT_SECRET_JSON': client_secret_str,
                'token.json': token_json
            }
        )
        
        # Try to update existing secret, create if doesn't exist
        try:
            v1.replace_namespaced_secret(SECRET_NAME, NAMESPACE, secret)
            logger.info(f"Updated secret {SECRET_NAME} in namespace {NAMESPACE}")
        except client.exceptions.ApiException as e:
            if e.status == 404:
                v1.create_namespaced_secret(NAMESPACE, secret)
                logger.info(f"Created secret {SECRET_NAME} in namespace {NAMESPACE}")
            else:
                raise
        
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
            include_granted_scopes='true'
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
        
        # Save token to Kubernetes
        token_json = credentials.to_json()
        
        if save_token_to_kubernetes(token_json):
            session['authenticated'] = True
            logger.info("Successfully authenticated and saved token")
            return redirect(url_for('success'))
        else:
            raise Exception("Failed to save token to Kubernetes")
    
    except Exception as e:
        logger.error(f"Error in OAuth callback: {e}")
        session['error'] = str(e)
        return redirect(url_for('index'))


@app.route('/success')
def success():
    """Success page after authentication."""
    return render_template('success.html', secret_name=SECRET_NAME, namespace=NAMESPACE)


@app.route('/health')
def health():
    """Health check endpoint."""
    return {'status': 'healthy'}, 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)
