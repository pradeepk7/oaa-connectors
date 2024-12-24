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