#!/bin/bash

# Script to update MCP config file with actual Cognito client secret
# Usage: ./scripts/update-mcp-config.sh [profile]

set -e

PROFILE=${1:-default}
CONFIG_FILE="mcp-server-config.json"
REGION="us-west-2"

echo "🔍 Updating MCP configuration with actual client secret..."

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Config file $CONFIG_FILE not found. Run CDK deploy first."
    exit 1
fi

# Extract client ID and user pool ID from config
CLIENT_ID=$(jq -r '.authorization_configuration.client_id' "$CONFIG_FILE")
USER_POOL_ID=$(aws cognito-idp list-user-pools --max-results 10 --profile "$PROFILE" --region "$REGION" --query "UserPools[?Name=='prometheus-mcp-oauth-pool'].Id" --output text)

if [ -z "$USER_POOL_ID" ]; then
    echo "❌ Could not find Cognito User Pool. Make sure it's deployed."
    exit 1
fi

echo "📋 Found User Pool: $USER_POOL_ID"
echo "📋 Found Client ID: $CLIENT_ID"

# Get client secret
echo "🔐 Retrieving client secret..."
CLIENT_SECRET=$(aws cognito-idp describe-user-pool-client \
    --user-pool-id "$USER_POOL_ID" \
    --client-id "$CLIENT_ID" \
    --profile "$PROFILE" \
    --region "$REGION" \
    --query 'UserPoolClient.ClientSecret' \
    --output text)

if [ "$CLIENT_SECRET" = "None" ] || [ -z "$CLIENT_SECRET" ]; then
    echo "❌ Could not retrieve client secret. Make sure the client has a secret."
    exit 1
fi

# Update config file
echo "📝 Updating config file..."
jq --arg secret "$CLIENT_SECRET" '.authorization_configuration.client_secret = $secret' "$CONFIG_FILE" > "${CONFIG_FILE}.tmp"
mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"

echo "✅ Successfully updated $CONFIG_FILE with client secret"
echo "🔗 MCP Endpoint: $(jq -r '.endpoint' "$CONFIG_FILE")"
echo "🔑 Client ID: $(jq -r '.authorization_configuration.client_id' "$CONFIG_FILE")"
echo "🌐 Token URL: $(jq -r '.authorization_configuration.exchange_url' "$CONFIG_FILE")"

# Test token retrieval
echo ""
echo "🧪 Testing token retrieval..."
RESPONSE=$(curl -s -X POST "$(jq -r '.authorization_configuration.exchange_url' "$CONFIG_FILE")" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "grant_type=client_credentials&scope=prometheus-mcp-server/read prometheus-mcp-server/write" \
    -u "$CLIENT_ID:$CLIENT_SECRET")

if echo "$RESPONSE" | jq -e '.access_token' > /dev/null 2>&1; then
    echo "✅ Token retrieval successful!"
    echo "🎯 Your MCP server is ready to use!"
else
    echo "❌ Token retrieval failed:"
    echo "$RESPONSE"
fi
