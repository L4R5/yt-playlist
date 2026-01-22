# YouTube Cookies Setup

## Why Cookies Are Needed

YouTube occasionally requires authentication to confirm you're not a bot, especially when downloading many videos. The application uses your browser cookies to authenticate as if you're logged in.

## How to Export YouTube Cookies

### Method 1: Using Browser Extension (Recommended)

1. **Install a Cookie Export Extension:**
   - Chrome/Edge: [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
   - Firefox: [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)

2. **Export Cookies:**
   - Go to youtube.com and make sure you're logged in
   - Click the extension icon
   - Click "Export" or "Download"
   - Save the file as `cookies.txt`

### Method 2: Using yt-dlp (Alternative)

```bash
# Extract cookies from your browser
yt-dlp --cookies-from-browser chrome --cookies cookies.txt https://www.youtube.com/

# Or from Firefox
yt-dlp --cookies-from-browser firefox --cookies cookies.txt https://www.youtube.com/
```

## Using Cookies with Docker

### Method 1: As Environment Variable (Recommended)

```bash
# Export cookies to variable
COOKIES=$(cat cookies.txt)

# Add to .env file
echo "COOKIES_CONTENT=$COOKIES" >> .env

# Run
docker-compose up -d
```

### Method 2: As File

```bash
# Copy cookies to data directory
cp cookies.txt data/

# Update .env
echo "COOKIES_FILE=/app/data/cookies.txt" >> .env

# Run
docker-compose up -d
```

## Using Cookies with Kubernetes

### Method 1: As Secret String (Recommended)

```bash
# Create secret from cookies file content
kubectl create secret generic yt-playlist-cookies \
  --from-literal=cookies="$(cat cookies.txt)"

# Update Helm values to use secret
helm upgrade yt-playlist yt-playlist/yt-playlist \
  --set-string download.cookiesContent="$(cat cookies.txt)"
```

Or via values file:
```yaml
download:
  cookiesContent: |
    # Netscape HTTP Cookie File
    .youtube.com	TRUE	/	TRUE	1234567890	VISITOR_INFO1_LIVE	abcdef...
    # ... rest of cookies
```

### Method 2: As File Mount (Alternative)

```bash
# Create secret from cookies file
kubectl create secret generic yt-playlist-cookies \
  --from-file=cookies.txt=cookies.txt

# Update your Helm values
helm upgrade yt-playlist yt-playlist/yt-playlist \
  --set download.cookiesFile=/app/cookies/cookies.txt \
  --set-file cookies.cookiesSecret=yt-playlist-cookies
```

**Manual Mount (if secret already exists):**

Add to your `values.yaml`:
```yaml
download:
  cookiesFile: /app/cookies/cookies.txt

# Add extra volume mount in deployment
extraVolumeMounts:
  - name: cookies
    mountPath: /app/cookies
    readOnly: true

extraVolumes:
  - name: cookies
    secret:
      secretName: yt-playlist-cookies
```

## Security Notes

⚠️ **Important:**
- Cookies give full access to your YouTube account
- Never commit `cookies.txt` to git
- Rotate cookies periodically by re-exporting from browser
- Use Kubernetes secrets, not ConfigMaps, for cookie storage
- Cookies expire - you may need to refresh them occasionally

## Troubleshooting

**Error: "Sign in to confirm you're not a bot"**
- Your cookies file is missing, invalid, or expired
- Re-export cookies from your browser
- Make sure the cookies file path is correct

**Cookies not working:**
```bash
# Check if cookies file exists
docker exec yt-playlist ls -la /app/data/cookies.txt

# Check environment variable
docker exec yt-playlist env | grep COOKIES_FILE

# Test with yt-dlp directly
yt-dlp --cookies cookies.txt https://www.youtube.com/watch?v=VIDEO_ID
```

**Kubernetes:**
```bash
# Check if secret exists
kubectl get secret yt-playlist-cookies

# Check if file is mounted
kubectl exec deployment/yt-playlist -- ls -la /app/cookies/

# Check environment variable
kubectl exec deployment/yt-playlist -- env | grep COOKIES_FILE
```
