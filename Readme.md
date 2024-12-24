# Veza OAA Connectors

This repository contains Open Authorization API (OAA) connectors for integrating various enterprise applications with Veza's authorization platform. These connectors enable organizations to analyze, monitor, and manage authorization across their technology stack.

## What is OAA?

Open Authorization API (OAA) is Veza's framework for importing identity and authorization metadata from custom applications and services. OAA enables you to:

- Map identities across systems
- Define authorization relationships
- Analyze access patterns
- Monitor compliance
- Manage permissions

## Project Structure

```
.
├── README.md
├── requirements.txt
└── connectors/
    ├── sailpoint-identitynow/
    │   ├── README.md
    │   ├── oaa_sailpoint-identitynow.py
    │   └── requirements.txt
    └── workboard/
        ├── README.md
        ├── oaa_workboard.py
        └── requirements.txt
```

## Available Connectors

### SailPoint IdentityNow Connector

The SailPoint IdentityNow connector synchronizes identity and access data from SailPoint's cloud-based identity platform. It captures:

- User identities and profiles
- Role assignments
- Access permissions
- Organizational relationships
- Custom attributes

[Learn more about the SailPoint connector](connectors/sailpoint-identitynow)

### WorkBoard Connector

The WorkBoard connector integrates user and team data from WorkBoard's OKR and strategy execution platform. It provides:

- User profile synchronization
- Organizational hierarchy mapping
- Role-based access mapping
- Custom attribute integration

[Learn more about the WorkBoard connector](connectors/workboard)

## Common Features

Both connectors share common functionality:

- Robust error handling
- Automatic retries with backoff
- Detailed logging
- SSL certificate verification
- Rate limiting support
- Data validation
- Incremental updates

## Architecture

The connectors follow a consistent architecture:

1. **Authentication Layer**
   - Token management
   - Session handling
   - SSL verification

2. **API Integration Layer**
   - Request handling
   - Response parsing
   - Rate limiting
   - Error handling

3. **Data Processing Layer**
   - Entity mapping
   - Permission translation
   - Data validation
   - Custom attribute handling

4. **OAA Integration Layer**
   - Provider management
   - Data source configuration
   - Entity synchronization
   - Permission mapping

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Access to target application API
- Veza instance with API access
- Network connectivity to services

### Installation

1. Clone this repository:
```bash
git clone https://github.com/pradeepk7/veza-oaa-connectors.git
cd veza-oaa-connectors
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure connector-specific requirements (see individual connector README files)

## Development

### Setting Up Development Environment

1. Create a virtual environment:
```bash
python -m venv ~/.venv/<app connector>
source ~/.venv/<app connector>/bin/activate  # Linux/Mac
.\venv\<app connector>\Scripts\activate   # Windows
```

2. Install development dependencies:
```bash
pip install -r requirements.txt
```

### Code Style

This project follows:
- PEP 8 style guide
- Google Python Style Guide
- Type hints for all functions
- Comprehensive docstrings

### Testing

Run tests with:
```bash
pytest
```

Generate coverage report:
```bash
pytest --cov=connectors
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) (WIP) for detailed guidelines.

## Security

- All credentials should be handled via environment variables
- SSL verification is enabled by default
- Rate limiting is implemented to prevent API abuse
- Token rotation is supported
- Minimal required permissions are used

Report security issues via GitHub Security Advisory.

## Best Practices

### Production Deployment

1. Use service accounts with minimal permissions
2. Implement proper secrets management
3. Enable monitoring and alerting
4. Set up centralized logging
5. Schedule regular sync intervals
6. Monitor API quotas and limits

### Error Handling

The connectors implement:
- Automatic retries for transient failures
- Exponential backoff
- Detailed error reporting
- Validation checks
- Rollback capabilities

### Performance

Optimize performance by:
- Using incremental updates
- Implementing batch processing
- Caching responses when appropriate
- Monitoring resource usage
- Setting appropriate timeouts

## Support

- GitHub Issues: Bug reports and feature requests
- Documentation: Individual connector README files
- Veza Support: Integration and platform issues

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Additional Resources

- [Veza OAA Documentation](https://docs.veza.com/oaa)
- [API References](https://api.veza.com)
- [Development Guidelines](https://docs.veza.com/development)
