#!/bin/bash

# Configuration
WORKBOARD_URL="${WORKBOARD_URL:-}"
WORKBOARD_TOKEN="${WORKBOARD_TOKEN:-}"
OUTPUT_FILE="workboard_users.json"
PAGE_SIZE=100
CURL_TIMEOUT=30

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

error() {
    echo -e "${RED}Error: $1${NC}" >&2
}

info() {
    echo -e "${GREEN}Info: $1${NC}"
}

warn() {
    echo -e "${YELLOW}Warning: $1${NC}"
}

# Check required environment variables
if [ -z "$WORKBOARD_URL" ]; then
    error "WORKBOARD_URL environment variable is not set"
    exit 1
fi

if [ -z "$WORKBOARD_TOKEN" ]; then
    error "WORKBOARD_TOKEN environment variable is not set"
    exit 1
fi

# Function to make API request
fetch_users() {
    local temp_file="temp_users.json"
    
    info "Fetching users..."
    
    # Make API request
    response_code=$(curl -s -w "%{http_code}" -o "$temp_file" \
        -H "Authorization: bearer $WORKBOARD_TOKEN" \
        -H "Accept: application/json" \
        --connect-timeout $CURL_TIMEOUT \
        --max-time $((CURL_TIMEOUT * 2)) \
        "${WORKBOARD_URL}/wb/apis/user/")
    
    # Check HTTP response code
    if [ "$response_code" != "200" ]; then
        error "Failed to fetch users (HTTP $response_code)"
        if [ -f "$temp_file" ]; then
            error "Response: $(cat "$temp_file")"
            rm "$temp_file"
        fi
        return 1
    fi
    
    # Check if response is valid JSON
    if ! jq empty "$temp_file" 2>/dev/null; then
        error "Invalid JSON response"
        rm "$temp_file"
        return 1
    fi
    
    # Check if request was successful
    if [ "$(jq -r '.success' "$temp_file")" != "true" ]; then
        error "API request failed: $(jq -r '.message' "$temp_file")"
        rm "$temp_file"
        return 1
    fi
    
    # Save the formatted response to output file
    jq '.' "$temp_file" > "$OUTPUT_FILE"
    
    # Get user details for summary
    local user_email=$(jq -r '.data.user.email' "$temp_file")
    local user_name=$(jq -r '.data.user.first_name + " " + .data.user.last_name' "$temp_file")
    
    rm "$temp_file"
    
    echo "Found user: $user_name ($user_email)"
}

# Main execution
{
    info "Starting WorkBoard users export..."
    info "Using WorkBoard URL: $WORKBOARD_URL"
    
    # Test connection
    info "Testing API connection..."
    if ! curl -s -f -H "Authorization: bearer $WORKBOARD_TOKEN" \
        "${WORKBOARD_URL}/wb/apis/user/" >/dev/null; then
        error "Failed to connect to WorkBoard API. Please check URL and credentials."
        exit 1
    fi
    
    # Fetch users
    if ! fetch_users; then
        error "Failed to fetch users"
        exit 1
    fi
    
    # Validate final JSON
    if ! jq empty "$OUTPUT_FILE" 2>/dev/null; then
        error "Final JSON validation failed"
        exit 1
    fi
    
    info "Successfully exported users to $OUTPUT_FILE"
    
    # Pretty print summary
    echo
    echo "Summary:"
    echo "--------"
    echo "Output file: $OUTPUT_FILE"
    echo "File size: $(ls -lh "$OUTPUT_FILE" | awk '{print $5}')"
    echo
    echo "User details:"
    jq -r '.data.user | "Name: \(.first_name) \(.last_name)\nEmail: \(.email)\nRole: \(.profile.title)\nCompany: \(.profile.company)"' "$OUTPUT_FILE"
    echo
    
} 2>&1 | tee workboard_users_export.log

# Check if any errors occurred
if grep -q "Error:" workboard_users_export.log; then
    error "Export completed with errors. Check workboard_users_export.log for details."
    exit 1
fi

exit 0