#!/bin/bash
# Configure GitLab Container Registry cleanup policies via glab CLI
# Requires: glab CLI authenticated (already set up in this project)

# Project path (will be URL-encoded)
PROJECT_PATH="${CI_PROJECT_PATH:-l4r51/yt-playlist}"
PROJECT_ID="${CI_PROJECT_ID}"

# If numeric ID not available, URL-encode the path
if [ -z "$PROJECT_ID" ]; then
  PROJECT_ID=$(echo "$PROJECT_PATH" | sed 's/\//%2F/g')
fi

# Configuration values (customize these)
ENABLED=${CLEANUP_ENABLED:-true}
CADENCE=${CLEANUP_CADENCE:-1d}
KEEP_N=${CLEANUP_KEEP_N:-10}
OLDER_THAN=${CLEANUP_OLDER_THAN:-30d}
NAME_REGEX=${CLEANUP_NAME_REGEX:-'.*'}

echo "Configuring container registry cleanup policies for project $PROJECT_ID..."

# Configure cleanup policy using glab api with JSON input
# Docs: https://docs.gitlab.com/ee/api/container_registry.html#update-the-cleanup-policy-for-a-container-registry
RESULT=$(glab api -X PUT "/projects/${PROJECT_ID}" \
  -H "Content-Type: application/json" \
  --input - <<EOF
{
  "container_expiration_policy_attributes": {
    "enabled": ${ENABLED},
    "cadence": "${CADENCE}",
    "keep_n": ${KEEP_N},
    "older_than": "${OLDER_THAN}",
    "name_regex": "${NAME_REGEX}"
  }
}
EOF
)

echo "$RESULT" | jq '.container_expiration_policy'

echo ""
echo "Cleanup policy configured:"
echo "  - Enabled: $ENABLED"
echo "  - Keep newest: $KEEP_N tags per repository"
echo "  - Delete tags older than: $OLDER_THAN"
echo "  - Runs: Daily at midnight UTC (cadence: $CADENCE)"
echo "  - Name regex: $NAME_REGEX (tags matching this are considered for deletion)"
echo ""
echo "To verify, run:"
echo "  glab api /projects/${PROJECT_ID} | jq '.container_expiration_policy'"
