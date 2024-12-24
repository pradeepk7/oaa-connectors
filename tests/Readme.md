# Tests and Utilities

This directory contains exploratory tests and utility scripts for working with the Veza OAA (Open Authorization API) connectors. These scripts help developers understand the OAA client library functionality and test integrations with various services.

## Overview

The test files are divided into three categories:
1. OAA Client Library Exploration (`pytest1-8.py`)
2. SailPoint User Management (`sailpoint_users.py`)
3. WorkBoard User Management (`workboard_users.sh`)

## OAA Client Library Exploration Tests

These Python scripts explore different aspects of the OAA client library and serve as learning tools for developers.

### pytest1.py - CustomIdPProvider Exploration
```python
# Examines CustomIdPProvider class signature and available methods
# Usage: python pytest1.py
```

### pytest2.py - CustomApplication Testing
```python
# Tests CustomApplication initialization and attributes
# Shows minimum required parameters
# Usage: python pytest2.py
```

### pytest3.py - CustomIdPUser Analysis
```python
# Examines CustomIdPUser class signature and methods
# Usage: python pytest3.py
```

### pytest4.py - Provider Creation Test
```python
# Tests creation of a basic CustomIdPProvider instance
# Shows available methods and initialization parameters
# Usage: python pytest4.py
```

### pytest5.py - Permission Definition Analysis
```python
# Examines CustomApplication permission definition methods
# Usage: python pytest5.py
```

### pytest6.py - Permission Class Discovery
```python
# Lists all permission-related classes in the templates module
# Usage: python pytest6.py
```

### pytest7.py - CustomPermission Analysis
```python
# Shows CustomPermission class signature and initialization parameters
# Usage: python pytest7.py
```

### pytest8.py - Provider Method Enumeration
```python
# Lists available methods on a CustomIdPProvider instance
# Usage: python pytest8.py
```

## SailPoint Integration Utilities

### sailpoint_users.py
A command-line utility for exporting user data from SailPoint IdentityNow.

#### Features
- Supports JSON and CSV output formats
- Configurable pagination
- Filtering and sorting capabilities
- Rate limiting handling

#### Usage
```bash
python sailpoint_users.py [--format {json,csv}] [--limit LIMIT] [--offset OFFSET] 
                         [--count] [--filters FILTERS] [--sorters SORTERS] 
                         [--output-dir OUTPUT_DIR]
```

#### Environment Variables
```bash
SAILPOINT_TENANT="your-tenant"
SAILPOINT_CLIENT_ID="your-client-id"
SAILPOINT_CLIENT_SECRET="your-client-secret"
```

#### Examples
```bash
# Export as JSON with default settings
python sailpoint_users.py

# Export as CSV with filtering
python sailpoint_users.py --format csv --filters "sourceId eq \"123\""

# Export with sorting
python sailpoint_users.py --sorters "name,created"
```

## WorkBoard Integration Utilities

### workboard_users.sh
A shell script for exporting user data from WorkBoard.

#### Features
- JSON output format
- Detailed logging
- Error handling
- Connection testing

#### Usage
```bash
./workboard_users.sh
```

#### Environment Variables
```bash
WORKBOARD_URL="https://your-instance.workboard.com"
WORKBOARD_TOKEN="your-api-token"
```

#### Output
- Creates `workboard_users.json` with user data
- Generates `workboard_users_export.log` with execution logs

## Development Notes

### Running Tests
1. Set up required environment variables for each service
2. Run individual test files as needed
3. Check output and logs for results

### Best Practices
- Always use a test environment when possible
- Don't run these scripts against production without understanding their impact
- Monitor API rate limits when running bulk operations
- Review logs for errors and warnings

### Common Issues
1. Authentication Failures
   - Verify environment variables are set correctly
   - Check API credentials
   - Ensure proper permissions

2. Rate Limiting
   - Adjust batch sizes and delays
   - Monitor API quotas
   - Use appropriate pagination settings

3. SSL/TLS Issues
   - Check certificate validity
   - Verify SSL configuration
   - Ensure proper CA certificates

## Contributing
1. Add appropriate error handling
2. Include comments and documentation
3. Test with various data scenarios
4. Update this README when adding new tests

## Security Notes
- Never commit credentials to version control
- Use environment variables for sensitive data
- Monitor API token usage
- Review logs for unauthorized access attempts

## License
These test utilities are subject to the same license as the main project.