#!/usr/bin/env python3
"""
SailPoint IdentityNow OAA Connector

This module implements a connector between SailPoint IdentityNow and Veza's OAA platform.
It synchronizes identity and access data from SailPoint to Veza for security analysis
and compliance monitoring.

Requires environment variables:
    SAILPOINT_TENANT: SailPoint tenant name
    SAILPOINT_CLIENT_ID: OAuth client ID
    SAILPOINT_CLIENT_SECRET: OAuth client secret
    VEZA_URL: Veza instance URL
    VEZA_API_KEY: Veza API key
    VERIFY_SSL: Optional, defaults to true
"""

import json
import logging
import logging.config
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Generator, Union
from urllib.parse import urljoin

import certifi
import requests
import urllib3
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from requests.packages.urllib3.util.retry import Retry
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    before_log,
    after_log,
    retry_if_exception_type
)

from oaaclient.client import OAAClient, OAAClientError
from oaaclient.templates import CustomApplication, OAAPermission, OAAPropertyType

# Environment variable names
SAILPOINT_TENANT = "SAILPOINT_TENANT"
SAILPOINT_CLIENT_ID = "SAILPOINT_CLIENT_ID" 
SAILPOINT_CLIENT_SECRET = "SAILPOINT_CLIENT_SECRET"
VEZA_URL = "VEZA_URL"
VEZA_API_KEY = "VEZA_API_KEY"
VERIFY_SSL = "VERIFY_SSL"

# Constants
MAX_LIMIT = 250  # Maximum items per API page
BATCH_SIZE = 1000  # Items to process in memory at once
MAX_RETRIES = 3
RETRY_WAIT_MULTIPLIER = 1
RETRY_WAIT_MIN = 4
RETRY_WAIT_MAX = 10
DEFAULT_TIMEOUT = 30  # seconds
DEFAULT_RATE_LIMIT = 1.0  # seconds between requests

# Configure logging
logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
        },
    },
    'loggers': {
        '': {
            'handlers': ['default'],
            'level': 'INFO',
            'propagate': True
        }
    }
})

logger = logging.getLogger(__name__)

# SailPoint Icon for Provider (base64 encoded)
SAILPOINT_ICON_B64 = (
    "PHN2ZyB2ZXJzaW9uPSIxLjEiIGlkPSJMYXllcl8xIiB4bWxuczp4PSJuc19leHRlbmQ7IiB4bWxuczpp"
    "PSJuc19haTsiIHhtbG5zOmdyYXBoPSJuc19ncmFwaHM7IiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcv"
    "MjAwMC9zdmciIHhtbG5zOnhsaW5rPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5L3hsaW5rIiB4PSIwcHgi"
    "IHk9IjBweCIgdmlld0JveD0iMCAwIDEwOS41IDEwNyIgc3R5bGU9ImVuYWJsZS1iYWNrZ3JvdW5kOm5l"
    "dyAwIDAgMTA5LjUgMTA3OyIgeG1sOnNwYWNlPSJwcmVzZXJ2ZSI+CiA8c3R5bGUgdHlwZT0idGV4dC9j"
    "c3MiPgogIC5zdDB7ZmlsbDojMDAzM0ExO30KCS5zdDF7ZmlsbDojQ0MyN0IwO30KCS5zdDJ7ZmlsbDoj"
    "MDA3MUNFO30KCS5zdDN7ZmlsbDojRTE3RkQyO30KIDwvc3R5bGU+CiA8bWV0YWRhdGE+CiAgPHNmdyB4"
    "bWxucz0ibnNfc2Z3OyI+CiAgIDxzbGljZXM+CiAgIDwvc2xpY2VzPgogICA8c2xpY2VTb3VyY2VCb3Vu"
    "ZHMgYm90dG9tTGVmdE9yaWdpbj0idHJ1ZSIgaGVpZ2h0PSIxMDciIHdpZHRoPSIxMDkuNSIgeD0iLTE2"
    "Ny41IiB5PSItMjEuNSI+CiAgIDwvc2xpY2VTb3VyY2VCb3VuZHM+CiAgPC9zZnc+CiA8L21ldGFkYXRh"
    "PgogPGc+CiAgPHBhdGggY2xhc3M9InN0MCIgZD0iTTYzLDBsMTMuMiw3OC42SDBMNjMsMHoiPgogIDwv"
    "cGF0aD4KICA8cGF0aCBjbGFzcz0ic3QxIiBkPSJNNjIuOSwwbDQ2LjcsNzguNkg3Nkw2Mi45LDB6Ij4K"
    "ICA8L3BhdGg+CiAgPHBhdGggY2xhc3M9InN0MiIgZD0iTTAsNzguNmg3Ni4ybDQuOCwyOC40TDAsNzgu"
    "NnoiPgogIDwvcGF0aD4KICA8cGF0aCBjbGFzcz0ic3QzIiBkPSJNNzYsNzguNmgzMy41TDgwLjgsMTA3"
    "TDc2LDc4LjZ6Ij4KICA8L3BhdGg+CiA8L2c+Cjwvc3ZnPg=="
)

@dataclass
class IdentityData:
    """
    Data class representing a SailPoint identity.
    
    Attributes:
        id: Unique identifier
        name: Display name
        email: Email address
        status: Current status
        created: Creation timestamp
        last_login: Last login timestamp
        groups: List of associated groups
    """
    id: str
    name: str
    email: Optional[str] = None
    status: Optional[str] = None
    created: Optional[str] = None
    last_login: Optional[str] = None
    groups: List[Dict[str, str]] = field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'IdentityData':
        """
        Create an IdentityData instance from API response data.
        
        Args:
            data: Raw API response dictionary
            
        Returns:
            IdentityData instance
            
        Raises:
            ValueError: If required fields are missing
        """
        if not data.get("id"):
            raise ValueError("Identity must have an ID")
            
        return cls(
            id=data["id"],
            name=data.get("name", ""),
            email=data.get("email"),
            status=data.get("status"),
            created=format_timestamp(data.get("created")),
            last_login=format_timestamp(data.get("lastLogin")),
            groups=data.get("groups", [])
        )

class SailPointError(Exception):
    """Base exception for SailPoint integration errors"""
    pass

class ConfigurationError(SailPointError):
    """Exception for configuration related errors"""
    pass

class APIError(SailPointError):
    """Exception for API related errors"""
    def __init__(self, message: str, status_code: Optional[int] = None,
                 response: Optional[requests.Response] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response

def get_required_env_var(var_name: str) -> str:
    """
    Get a required environment variable or raise an error if it's not set.
    
    Args:
        var_name: Name of the environment variable
        
    Returns:
        str: Value of the environment variable
        
    Raises:
        ConfigurationError: If the environment variable is not set
    """
    value = os.getenv(var_name)
    if value is None:
        raise ConfigurationError(
            f"Required environment variable '{var_name}' is not set. "
            "Please set this variable before running the integration."
        )
    return value

def get_optional_env_var(var_name: str, default: Any) -> Any:
    """
    Get an optional environment variable with a default value.
    
    Args:
        var_name: Name of the environment variable
        default: Default value if the environment variable is not set
        
    Returns:
        The environment variable value or the default value
    """
    return os.getenv(var_name, default)

def format_timestamp(ts: Optional[Union[int, str]]) -> Optional[str]:
    """
    Format timestamp to ISO format.
    
    Args:
        ts: Unix timestamp in milliseconds or ISO string
        
    Returns:
        str: ISO formatted timestamp or None if input is invalid
    """
    if not ts:
        return None
        
    try:
        if isinstance(ts, str):
            # If it's already an ISO string, validate and return
            datetime.fromisoformat(ts.replace('Z', '+00:00'))
            return ts
        # Convert milliseconds to ISO
        return datetime.fromtimestamp(ts/1000, timezone.utc).isoformat()
    except Exception as e:
        logger.warning(f"Error formatting timestamp {ts}: {e}")
        return None

class SailPointOAAProvider:
    """
    OAA Provider for SailPoint IdentityNow integration.
    Handles authentication, data fetching, and synchronization with Veza.
    """
    
    def __init__(self, oaa_client: OAAClient, verify_ssl: bool = True,
                 rate_limit: float = DEFAULT_RATE_LIMIT):
        """
        Initialize the SailPoint OAA Provider.
        
        Args:
            oaa_client: OAA client instance
            verify_ssl: Whether to verify SSL certificates
            rate_limit: Minimum seconds between API calls
        """
        self.tenant = get_required_env_var(SAILPOINT_TENANT)
        self.client_id = get_required_env_var(SAILPOINT_CLIENT_ID)
        self.client_secret = get_required_env_var(SAILPOINT_CLIENT_SECRET)
        self.oaa_client = oaa_client
        self._setup_session(verify_ssl)
        self.rate_limit = rate_limit
        self._last_request_time = 0
        
        # Set up base URLs
        self.api_base_url = f"https://{self.tenant}.api.identitynow.com"
        self.token_url = urljoin(self.api_base_url, "/oauth/token")
        
        self.logger = logging.getLogger(__name__)

    def _setup_session(self, verify_ssl: bool) -> None:
        """Configure requests session with proper SSL and retry settings."""
        self.session = requests.Session()
        
        if not verify_ssl:
            self.session.verify = False
            urllib3.disable_warnings(InsecureRequestWarning)
        else:
            self.session.verify = certifi.where()
            
        # Configure retry strategy
        retry_strategy = Retry(
            total=MAX_RETRIES,
            backoff_factor=RETRY_WAIT_MULTIPLIER,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=100,
            pool_maxsize=100
        )
        self.session.mount("https://", adapter)

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=RETRY_WAIT_MULTIPLIER, 
                            min=RETRY_WAIT_MIN,
                            max=RETRY_WAIT_MAX),
        retry=retry_if_exception_type(RequestException),
        before=before_log(logger, logging.DEBUG),
        after=after_log(logger, logging.DEBUG)
    )
    def authenticate(self) -> None:
        """
        Authenticate with SailPoint IdentityNow and get access token.
        
        Raises:
            APIError: If authentication fails
        """
        try:
            self.logger.debug(f"Attempting authentication to {self.token_url}")
            
            data = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }
            
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded',
                'scope': 'sp:scope:all'
            }
            
            response = self.session.post(
                self.token_url,
                data=data,
                headers=headers,
                timeout=DEFAULT_TIMEOUT
            )
            
            response.raise_for_status()
            token_data = response.json()
            
            self.session.headers.update({
                'Authorization': f'Bearer {token_data["access_token"]}',
                'Accept': 'application/json'
            })
            
            self.logger.info("Successfully authenticated to SailPoint")
            
        except RequestException as e:
            raise APIError(
                f"Authentication failed: {str(e)}",
                status_code=getattr(e.response, 'status_code', None),
                response=getattr(e, 'response', None)
            )

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Make an API request with rate limiting and error handling.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional arguments for requests
            
        Returns:
            Response object
            
        Raises:
            APIError: If the request fails
        """
        url = urljoin(self.api_base_url, f"/v3/{endpoint}")
        
        try:
            response = self.session.request(
                method,
                url,
                timeout=DEFAULT_TIMEOUT,
                **kwargs
            )
            response.raise_for_status()
            return response
            
        except RequestException as e:
            raise APIError(
                f"API request failed: {str(e)}",
                status_code=getattr(e.response, 'status_code', None),
                response=getattr(e, 'response', None)
            )

    def get_paginated_results(self, endpoint: str, query: Dict[str, Any]) -> Generator[Dict[str, Any], None, None]:
        """
        Get paginated results from the SailPoint API.
        
        Args:
            endpoint: API endpoint to query
            query: Base query parameters
                
        Yields:
            Individual items from the API response
            
        Raises:
            APIError: If API request fails
        """
        offset = 0
        total_processed = 0
        
        while True:
            params = {
                'limit': min(query.get('limit', MAX_LIMIT), MAX_LIMIT),
                'offset': offset,
                'count': 'true'
            }
            
            # Add any additional query parameters
            if filters := query.get('filters'):
                params['filters'] = filters
            if sorters := query.get('sorters'):
                params['sorters'] = sorters
                
            try:
                # Make API request
                response = self._make_request('GET', endpoint, params=params)
                
                # Get items and total count
                items = response.json()
                total = int(response.headers.get('X-Total-Count', 0))
                
                if not items:
                    break
                    
                # Yield individual items
                for item in items:
                    yield item
                    total_processed += 1
                    
                # Log progress for large result sets
                if total_processed % 1000 == 0:
                    self.logger.info(f"Processed {total_processed} of {total} items")
                
                # Check if we've processed everything
                offset += len(items)
                if offset >= total:
                    break
                    
            except APIError as e:
                self.logger.error(f"Failed to fetch page at offset {offset}: {str(e)}")
                raise

    def fetch_identities(self) -> List[Dict[str, Any]]:
        """
        Fetch all identities from SailPoint.
        
        Returns:
            List of identity dictionaries
            
        Raises:
            APIError: If fetching fails
        """
        identities = []
        query = {'limit': MAX_LIMIT}
        
        try:
            for identity in self.get_paginated_results('public-identities', query):
                identities.append(identity)
                
            self.logger.info(f"Fetched {len(identities)} identities")
            return identities
            
        except APIError as e:
            self.logger.error(f"Failed to fetch identities: {str(e)}")
            raise

    def process_identities_batch(
        self,
        provider_data: CustomApplication,
        identities: List[Dict[str, Any]]
    ) -> None:
        """
        Process a batch of identities and add them to the provider data.
        
        Args:
            provider_data: CustomApplication instance to add users to
            identities: List of identity dictionaries to process
            
        Raises:
            ValueError: If batch processing fails
        """
        processed = 0
        errors = 0
        
        for raw_identity in identities:
            try:
                # Parse and validate identity data
                identity = IdentityData.from_api_response(raw_identity)
                
                # Create or update user
                user = provider_data.add_local_user(
                    name=identity.name,
                    identities=[identity.email] if identity.email else [],
                    unique_id=identity.id
                )
                
                # Set standard properties
                user.is_active = True
                user.created_at = identity.created
                user.last_login_at = identity.last_login
                
                # Set custom properties
                user.set_property("sailpoint_id", identity.id)
                if identity.email:
                    user.set_property("email", identity.email)
                if identity.status:
                    user.set_property("status", identity.status)
                
                # Process groups
                for group in identity.groups:
                    if group_name := group.get("name"):
                        try:
                            if group_name not in provider_data.local_groups:
                                provider_data.add_local_group(
                                    name=group_name,
                                    unique_id=group.get("id", group_name)
                                )
                            user.add_group(group_name)
                        except Exception as e:
                            self.logger.warning(
                                f"Error adding user {identity.id} to group {group_name}: {str(e)}"
                            )
                
                # Add permissions if email exists
                if identity.email:
                    user.add_permission(
                        permission="access",
                        apply_to_application=True
                    )
                
                processed += 1
                    
            except ValueError as e:
                self.logger.error(f"Invalid identity data: {str(e)}")
                errors += 1
            except Exception as e:
                self.logger.error(f"Error processing identity: {str(e)}")
                errors += 1
                
        self.logger.info(
            f"Processed {processed} identities with {errors} errors"
        )
        
        if errors > 0:
            self.logger.warning(
                f"Encountered {errors} errors while processing identities"
            )

    def sync(self, force: bool = False) -> None:
        """
        Sync SailPoint data to OAA.
        
        Args:
            force: If True, delete and recreate provider
            
        Raises:
            ConfigurationError: If configuration is invalid
            APIError: If API operations fail
        """
        try:
            # Authenticate first
            self.authenticate()
            
            provider_name = "SailPoint IdentityNow"
            data_source_name = f"SailPoint - {self.tenant}"

            # Handle provider cleanup if force flag is set
            if force:
                self.cleanup_provider(provider_name)

            # Create or get provider
            provider = self._get_or_create_provider(provider_name)
            
            # Create base provider payload
            provider_data = self._create_provider_data()
            
            # Fetch and process identities
            self.logger.info("Fetching identities...")
            identities = self.fetch_identities()
            
            # Process identities in batches
            total_identities = len(identities)
            self.logger.info(
                f"Processing {total_identities} identities in batches of {BATCH_SIZE}"
            )
            
            for i in range(0, total_identities, BATCH_SIZE):
                batch = identities[i:i + BATCH_SIZE]
                self.logger.debug(
                    f"Processing batch {i//BATCH_SIZE + 1} of "
                    f"{(total_identities + BATCH_SIZE - 1)//BATCH_SIZE}"
                )
                self.process_identities_batch(provider_data, batch)
        
            self.logger.info(f"Processed {total_identities} identities")
            
            # Push data to OAA
            self._push_to_oaa(provider_name, data_source_name, provider_data)
            
        except Exception as e:
            self.logger.error(f"Sync failed: {str(e)}")
            self.logger.debug("Exception details:", exc_info=True)
            raise

    def _get_or_create_provider(self, provider_name: str) -> Dict[str, Any]:
        """
        Get existing provider or create new one.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Provider dictionary
        """
        provider = self.oaa_client.get_provider(provider_name)
        if not provider:
            self.logger.info(f"Creating new provider: {provider_name}")
            provider = self.oaa_client.create_provider(
                name=provider_name,
                custom_template="application"
            )
            self.logger.info(f"Created provider with ID: {provider['id']}")
            
            # Set provider icon if available
            if SAILPOINT_ICON_B64:
                try:
                    self.oaa_client.update_provider_icon(
                        provider['id'],
                        SAILPOINT_ICON_B64
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to update provider icon: {e}")
        else:
            self.logger.info(f"Found existing provider: {provider_name}")
            
        return provider

    def _create_provider_data(self) -> CustomApplication:
        """
        Create and configure the base provider data structure.
        
        Returns:
            Configured CustomApplication instance
        """
        provider_data = CustomApplication(
            name="SailPoint IdentityNow",
            application_type="IDaaS",
            description="SailPoint IdentityNow Integration"
        )
        
        # Define custom properties
        provider_data.property_definitions.define_local_user_property(
            "sailpoint_id", 
            OAAPropertyType.STRING
        )
        provider_data.property_definitions.define_local_user_property(
            "email", 
            OAAPropertyType.STRING
        )
        provider_data.property_definitions.define_local_user_property(
            "status", 
            OAAPropertyType.STRING
        )
        
        # Define custom permissions
        provider_data.add_custom_permission(
            "access",
            [OAAPermission.DataRead, OAAPermission.DataWrite]
        )
        
        return provider_data

    def _push_to_oaa(
        self,
        provider_name: str,
        data_source_name: str,
        provider_data: CustomApplication
    ) -> None:
        """
        Push provider data to OAA.
        
        Args:
            provider_name: Name of the provider
            data_source_name: Name of the data source
            provider_data: Populated CustomApplication instance
            
        Raises:
            OAAClientError: If push fails
        """
        self.logger.info("Pushing data to OAA...")
        
        try:
            response = self.oaa_client.push_application(
                provider_name=provider_name,
                data_source_name=data_source_name,
                application_object=provider_data,
                create_provider=True
            )
            
            if response.get("warnings"):
                for warning in response["warnings"]:
                    self.logger.warning(f"Push warning: {warning}")
                    
            self.logger.info("Sync completed successfully")
            
        except OAAClientError as e:
            self.logger.error(f"Error pushing to OAA: {str(e)}")
            if hasattr(e, 'details'):
                for detail in e.details:
                    self.logger.error(f"Detail: {detail}")
            raise

def main():
    """
    Main function to run the SailPoint OAA integration.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='SailPoint OAA Integration')
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force provider recreation'
    )
    parser.add_argument(
        '--verify-ssl',
        action='store_true',
        help='Verify SSL certificates'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set the logging level'
    )
    args = parser.parse_args()
    
    # Set logging level based on argument
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    try:
        # Get Veza configuration
        veza_url = get_required_env_var(VEZA_URL)
        veza_api_key = get_required_env_var(VEZA_API_KEY)
        
        # Get SSL verification setting
        verify_ssl = get_optional_env_var(VERIFY_SSL, "true").lower() != "false"
        if args.verify_ssl:
            verify_ssl = True
        
        if not verify_ssl:
            logger.warning(
                "SSL certificate verification is disabled. "
                "This is not recommended for production environments."
            )
        
        # Initialize OAA client
        oaa_client = OAAClient(
            url=veza_url,
            api_key=veza_api_key
        )
        
        # Initialize and run provider
        provider = SailPointOAAProvider(
            oaa_client=oaa_client,
            verify_ssl=verify_ssl
        )
        
        provider.sync(force=args.force)
        
    except (ConfigurationError, APIError, OAAClientError) as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.debug("Exception details:", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
