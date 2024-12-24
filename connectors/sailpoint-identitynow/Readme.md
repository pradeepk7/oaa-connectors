# SailPoint IdentityNow OAA Connector

A Veza Open Authorization API (OAA) connector for synchronizing identity and access data from SailPoint IdentityNow. This connector enables organizations to integrate their SailPoint IdentityNow identity management data with Veza's authorization platform for comprehensive security analysis and compliance monitoring.

## Features

- Synchronizes user identities and profiles
- Maps SailPoint roles and permissions to Veza's authorization model
- Supports custom attributes and properties
- Handles pagination for large datasets
- Provides detailed logging and error reporting
- Supports SSL certificate verification configuration
- Implements automatic retries with exponential backoff

## Prerequisites

- Python 3.8 or higher
- Access to a SailPoint IdentityNow instance
- SailPoint API credentials (Client ID and Secret)
- Veza instance with API access
- Network access to both SailPoint and Veza APIs

## Installation

1. Clone this repository or download the connector files
2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

The connector requires the following environment variables:

| Variable | Description | Required |
|----------|-------------|----------|
| SAILPOINT_TENANT | Your SailPoint tenant name (e.g., "acme") | Yes |
| SAILPOINT_CLIENT_ID | OAuth client ID from SailPoint | Yes |
| SAILPOINT_CLIENT_SECRET | OAuth client secret from SailPoint | Yes |
| VEZA_URL | Veza instance URL | Yes |
| VEZA_API_KEY | Veza API key | Yes |
| VERIFY_SSL | Whether to verify SSL certificates (default: "true") | No |

### Setting up SailPoint API Access

1. Log in to your SailPoint IdentityNow admin console
2. Navigate to Admin > Security Settings > API Management
3. Create a new API client
4. Note the Client ID and Client Secret
5. Ensure the client has the following permissions:
   - `idn:all-identities:read`
   - `idn:role-membership:read`
   - `idn:identity-attributes:read`

### Setting up Veza API Access

1. Log in to your Veza instance
2. Navigate to Administration > API Keys
3. Create a new API key
4. Copy the API key value (it will only be shown once)

## Usage

### Basic Usage

1. Set the required environment variables:
```bash
export SAILPOINT_TENANT="your-tenant"
export SAILPOINT_CLIENT_ID="your-client-id"
export SAILPOINT_CLIENT_SECRET="your-client-secret"
export VEZA_URL="https://your-veza-instance.vezacloud.com"
export VEZA_API_KEY="your-veza-api-key"
```

2. Run the connector:
```bash
python oaa_sailpoint-identitynow.py
```

### Command Line Options

```bash
python oaa_sailpoint-identitynow.py [OPTIONS]

Options:
  --force           Force provider recreation
  --verify-ssl      Verify SSL certificates
  --log-level       Set logging level (DEBUG, INFO, WARNING, ERROR)
```

### Running in Production

For production deployments, consider:

1. Using a secrets management solution for credentials
2. Implementing proper logging to a centralized system
3. Setting up monitoring and alerting
4. Running on a schedule (e.g., using cron or a scheduler)
5. Using a service account with minimal required permissions

Example systemd service file:
```ini
[Unit]
Description=SailPoint OAA Connector
After=network.target

[Service]
Type=oneshot
User=oaa-service
Environment=SAILPOINT_TENANT=your-tenant
Environment=SAILPOINT_CLIENT_ID=your-client-id
Environment=SAILPOINT_CLIENT_SECRET=your-client-secret
Environment=VEZA_URL=your-veza-url
Environment=VEZA_API_KEY=your-veza-api-key
ExecStart=/usr/local/bin/python3 /opt/oaa/oaa_sailpoint-identitynow.py
```

## Data Mapping

| SailPoint Entity | Veza Entity | Notes |
|-----------------|-------------|-------|
| User | Local User | Includes custom attributes |
| Group | Local Group | With membership |
| Role | Permission | Mapped to Veza canonical permissions |
| Organization | Application Instance | Top-level container |

## Troubleshooting

### Common Issues

1. Authentication Failures
   - Verify client ID and secret are correct
   - Check API client permissions in SailPoint
   - Ensure tenant name is correct

2. SSL Certificate Errors
   - Verify SSL certificates are valid
   - Set VERIFY_SSL="false" for testing (not recommended for production)

3. Rate Limiting
   - The connector implements automatic retries
   - Check SailPoint API quotas and limits

### Logging

The connector uses Python's logging framework with configurable levels:

```bash
python oaa_sailpoint-identitynow.py --log-level DEBUG
```

Logs include:
- API request details
- Processing progress
- Errors and warnings
- Sync statistics

## Development

### Architecture

The connector follows a modular design:
1. Authentication and API interaction
2. Data fetching and pagination
3. Data transformation
4. OAA integration
5. Error handling and logging

### Adding Features

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## Support

- For connector issues: Submit a GitHub issue
- For SailPoint API issues: Contact SailPoint support
- For Veza integration issues: Contact Veza support

## License

MIT License - See LICENSE file for details
```

And for the WorkBoard connector:

```markdown
# WorkBoard OAA Connector

A Veza Open Authorization API (OAA) connector for integrating WorkBoard user and team data with Veza's authorization platform. This connector enables organizations to analyze and monitor access patterns within their WorkBoard instance.

## Features

- Synchronizes WorkBoard user profiles
- Maps organizational hierarchy
- Captures custom attributes
- Supports role-based access mapping
- Provides detailed logging
- Includes dry-run capability for testing

## Prerequisites

- Python 3.8 or higher
- WorkBoard instance with API access
- WorkBoard API token
- Veza instance with API access
- Network connectivity to both services

## Installation

1. Clone this repository or download the connector files
2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

The connector requires the following environment variables:

| Variable | Description | Required |
|----------|-------------|----------|
| WORKBOARD_URL | WorkBoard instance URL | Yes |
| WORKBOARD_TOKEN | WorkBoard API bearer token | Yes |
| VEZA_URL | Veza instance URL | Yes |
| VEZA_API_KEY | Veza API key | Yes |

### Setting up WorkBoard API Access

1. Log in to WorkBoard as an administrator
2. Navigate to Settings > API Configuration
3. Generate a new API token
4. Copy the token value (it will only be shown once)

### Setting up Veza API Access

1. Log in to your Veza instance
2. Navigate to Administration > API Keys
3. Create a new API key
4. Copy the API key value

## Usage

### Basic Usage

1. Set the required environment variables:
```bash
export WORKBOARD_URL="https://your-instance.workboard.com"
export WORKBOARD_TOKEN="your-api-token"
export VEZA_URL="https://your-veza-instance.vezacloud.com"
export VEZA_API_KEY="your-veza-api-key"
```

2. Run the connector:
```bash
python oaa_workboard.py
```

### Command Line Options

```bash
python oaa_workboard.py [OPTIONS]

Options:
  --log-level    Set logging level (DEBUG, INFO, WARNING, ERROR)
  --dry-run      Fetch data but don't push to OAA
  --save-json    Save fetched data to JSON file for debugging
```

### Testing

Use the dry-run mode to test the connector:
```bash
python oaa_workboard.py --dry-run --save-json
```

This will:
1. Fetch data from WorkBoard
2. Display user information
3. Save data to workboard_user.json if --save-json is specified
4. Skip pushing to Veza

## Data Mapping

| WorkBoard Entity | Veza Entity | Notes |
|-----------------|-------------|-------|
| User | Local User | Including custom attributes |
| Title | Property | Used for role determination |
| Manager | Property | Captures reporting structure |
| Custom Attributes | Properties | Mapped to custom properties |

### Permissions Mapping

| WorkBoard Role | Veza Permission | Capabilities |
|---------------|-----------------|--------------|
| Admin | admin | Full access |
| Regular User | user | Standard access |
| Viewer | viewer | Read-only access |

## Troubleshooting

### Common Issues

1. Authentication Errors
   - Verify API token is valid
   - Check token permissions
   - Ensure URLs are correct

2. Connection Issues
   - Verify network connectivity
   - Check firewall rules
   - Validate SSL certificates

3. Data Issues
   - Use --dry-run to verify data fetching
   - Check --save-json output
   - Verify user permissions

### Logging

Configure logging level for troubleshooting:
```bash
python oaa_workboard.py --log-level DEBUG
```

Log output includes:
- API requests and responses
- Data processing steps
- Error details
- Sync status

## Production Deployment

### Best Practices

1. Security:
   - Use a service account
   - Store credentials securely
   - Enable SSL verification
   - Implement audit logging

2. Reliability:
   - Schedule regular runs
   - Monitor execution
   - Set up alerts
   - Implement error reporting

3. Performance:
   - Run during off-peak hours
   - Monitor API rate limits
   - Optimize sync frequency

### Example Cron Configuration

```bash
# Run sync every 6 hours
0 */6 * * * /path/to/venv/bin/python /opt/oaa/oaa_workboard.py >> /var/log/oaa_workboard.log 2>&1
```

## Development

### Architecture

The connector implements:
1. WorkBoard API client
2. Data transformation
3. OAA integration
4. Error handling
5. Logging framework

### Extending the Connector

To add features:
1. Fork the repository
2. Create a feature branch
3. Implement changes
4. Submit pull request

## Support

- For connector issues: Submit a GitHub issue
- For WorkBoard API issues: Contact WorkBoard support
- For Veza integration issues: Contact Veza support

## License

MIT License - See LICENSE file for details