#!/usr/bin/env python3
"""
WorkBoard OAA Connector

This module implements a connector between WorkBoard and Veza's OAA platform.
It synchronizes user and team data from WorkBoard to Veza for security analysis.

Required environment variables:
    WORKBOARD_URL: WorkBoard instance URL (e.g. https://www.myworkboard.com)
    WORKBOARD_TOKEN: WorkBoard bearer token
    VEZA_URL: Veza instance URL 
    VEZA_API_KEY: Veza API key
"""

import logging
import logging.config
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException
from requests.packages.urllib3.util.retry import Retry

from oaaclient.client import OAAClient, OAAClientError
from oaaclient.templates import CustomApplication, OAAPermission, OAAPropertyType

# Icon constants
WORKBOARD_ICON_B64 = (
    "PHN2ZyB3aWR0aD0iMjUwMCIgaGVpZ2h0PSIyNTAwIiB2aWV3Qm94PSIwIDAgMjU2IDI1NiIgeG1sbnM9"
    "Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIiBwcmVzZXJ2ZUFzcGVjdFJhdGlvPSJ4TWlkWU1pZCI+"
    "PHBhdGggZD0iTTI1NiAxMjhjMCA3MC42OTItNTcuMzA4IDEyOC0xMjggMTI4QzU3LjMwOCAyNTYgMCAx"
    "OTguNjkyIDAgMTI4IDAgNTcuMzA4IDU3LjMwOCAwIDEyOCAwYzcwLjY5MiAwIDEyOCA1Ny4zMDggMTI4"
    "IDEyOCIgZmlsbD0iIzUxQkJENiIvPjxwYXRoIGQ9Ik0xMDEuOTggMTEwLjA3NlY3NS40MTRsNTUuODE2"
    "IDE4LjczMy01NS44MTYgMTUuOTI5em01NS44MTYgNTQuNzE1TDEwMS45OCAxODEuN3YtMzQuODc4bDU1"
    "LjgxNiAxNy45Njh6bTM2LjkzMi04My4wOTVsLTkyLjc0OC0zMy4wM1YzMi41OTZoLTI1LjZ2MTkwLjk1"
    "aDI1LjZ2LTE0Ljg2bDkyLjc0OC0yOC4zNjZ2LTI1LjZsLTY4LjQwNy0yNS42IDY4LjQwNy0yMS40MDN2"
    "LTI2LjAyeiIgZmlsbD0iI0ZGRiIvPjwvc3ZnPg=="
)

# Environment variables
WORKBOARD_URL = "WORKBOARD_URL"
WORKBOARD_TOKEN = "WORKBOARD_TOKEN"
VEZA_URL = "VEZA_URL"
VEZA_API_KEY = "VEZA_API_KEY"

# Constants
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3

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

@dataclass
class WorkBoardUser:
    """Data class representing a WorkBoard user based on actual API response."""
    user_id: str
    email: str
    first_name: str
    last_name: str
    wb_email: Optional[str] = None
    cell_num: Optional[str] = None
    create_at: Optional[int] = None
    last_visited_at: Optional[str] = None
    picture: Optional[str] = None
    time_zone: Optional[str] = None
    external_id: Optional[str] = None
    org_id: Optional[str] = None
    manager: List[Dict[str, Any]] = field(default_factory=list)
    profile: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'WorkBoardUser':
        """Create WorkBoardUser instance from API response data."""
        if not data.get("user_id"):
            raise ValueError("User must have a user_id")
        
        return cls(
            user_id=str(data["user_id"]),
            email=data.get("email", ""),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            wb_email=data.get("wb_email"),
            cell_num=data.get("cell_num"),
            create_at=data.get("create_at"),
            last_visited_at=data.get("last_visited_at"),
            picture=data.get("picture"),
            time_zone=data.get("time_zone"),
            external_id=data.get("external_id"),
            org_id=data.get("org_id"),
            manager=data.get("manager", []),
            profile=data.get("profile", {})
        )

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}".strip()

    def get_title(self) -> Optional[str]:
        """Get user's title from profile."""
        return self.profile.get("title")

    def get_company(self) -> Optional[str]:
        """Get user's company from profile."""
        return self.profile.get("company")

    def get_custom_attributes(self) -> Dict[str, str]:
        """Get user's custom attributes as a dictionary."""
        return {
            attr["name"]: attr["value"] 
            for attr in self.profile.get("custom_attributes", [])
            if "name" in attr and "value" in attr
        }

def format_timestamp(ts: Optional[Union[int, str]]) -> Optional[str]:
    """Format timestamp to ISO format."""
    if not ts:
        return None
    
    try:
        if isinstance(ts, str):
            # Convert string timestamp to integer
            ts = int(ts)
        # Convert epoch to ISO
        return datetime.fromtimestamp(ts, timezone.utc).isoformat()
    except (ValueError, TypeError) as e:
        logger.warning(f"Error formatting timestamp {ts}: {e}")
        return None

class WorkBoardError(Exception):
    """Base exception for WorkBoard integration errors."""
    pass

class ConfigurationError(WorkBoardError):
    """Exception for configuration related errors."""
    pass

class APIError(WorkBoardError):
    """Exception for API related errors."""
    def __init__(self, message: str, status_code: Optional[int] = None,
                 response: Optional[requests.Response] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response

def get_required_env_var(var_name: str) -> str:
    """Get required environment variable or raise error if not set."""
    value = os.getenv(var_name)
    if not value:
        raise ConfigurationError(f"Required environment variable '{var_name}' is not set")
    return value

class WorkBoardOAAProvider:
    """OAA Provider for WorkBoard integration."""
    
    def __init__(self, oaa_client: OAAClient):
        """Initialize the WorkBoard OAA Provider."""
        self.base_url = get_required_env_var(WORKBOARD_URL)
        self.token = get_required_env_var(WORKBOARD_TOKEN)
        self.oaa_client = oaa_client
        
        self._setup_session()
        self.logger = logging.getLogger(__name__)

    def _setup_session(self) -> None:
        """Configure requests session with retry settings."""
        self.session = requests.Session()
        
        retry_strategy = Retry(
            total=MAX_RETRIES,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        
        # Set auth header
        self.session.headers.update({
            'Authorization': f'bearer {self.token}',
            'Accept': 'application/json'
        })

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an API request with error handling."""
        url = urljoin(self.base_url, f"/wb/apis/{endpoint}")
        
        try:
            response = self.session.request(
                method,
                url,
                timeout=DEFAULT_TIMEOUT,
                **kwargs
            )
            response.raise_for_status()
            
            data = response.json()
            if not data.get("success"):
                raise APIError(f"API request failed: {data.get('message', 'Unknown error')}")
                
            return data
            
        except RequestException as e:
            raise APIError(
                f"API request failed: {str(e)}",
                status_code=getattr(e.response, 'status_code', None),
                response=getattr(e, 'response', None)
            )

    def fetch_user(self) -> WorkBoardUser:
        """Fetch current user data from WorkBoard."""
        try:
            response = self._make_request('GET', 'user/')
            user_data = response.get("data", {}).get("user", {})
            
            if not user_data:
                raise APIError("No user data in response")
                
            return WorkBoardUser.from_api_response(user_data)
            
        except APIError as e:
            self.logger.error(f"Failed to fetch user: {str(e)}")
            raise

    def process_user(self, provider_data: CustomApplication, user: WorkBoardUser) -> None:
        """Process a user and add to provider data."""
        try:
            # Create/update user
            oaa_user = provider_data.add_local_user(
                name=user.full_name,
                identities=[user.email] if user.email else [],
                unique_id=user.user_id
            )
            
            # Set standard properties
            oaa_user.created_at = format_timestamp(user.create_at)
            oaa_user.last_login_at = format_timestamp(user.last_visited_at)
            oaa_user.is_active = True  # Since we can fetch the user data, they must be active
            
            # Set custom properties
            oaa_user.set_property("workboard_id", user.user_id)
            oaa_user.set_property("email", user.email)
            if title := user.get_title():
                oaa_user.set_property("title", title)
            if company := user.get_company():
                oaa_user.set_property("company", company)
            
            # Process manager relationship
            for manager in user.manager:
                manager_id = manager.get("user_id")
                if manager_id:
                    oaa_user.set_property("manager_id", manager_id)
                    # Add manager role information if available
                    manager_role = manager.get("role")
                    if manager_role:
                        oaa_user.set_property("manager_role", manager_role)
                    break
            
            # Process custom attributes
            custom_attrs = user.get_custom_attributes()
            for attr_name, attr_value in custom_attrs.items():
                safe_name = attr_name.lower().replace(" ", "_")
                try:
                    oaa_user.set_property(f"custom_{safe_name}", attr_value)
                except Exception as e:
                    self.logger.warning(f"Failed to set custom attribute {attr_name}: {e}")
            
            # Add role-based permission based on title and role
            is_admin = any([
                title and "admin" in title.lower() for title in [
                    user.get_title(),
                    manager.get("role", "").lower() if user.manager else None
                ] if title
            ])
            
            role = "admin" if is_admin else "user"
            oaa_user.add_permission(permission=role, apply_to_application=True)
            
        except Exception as e:
            self.logger.error(f"Error processing user {user.user_id}: {str(e)}")
            raise

    def sync(self) -> None:
        """Sync WorkBoard data to OAA."""
        try:
            provider_name = "WorkBoard"
            data_source_name = f"WorkBoard - {self.base_url.split('//')[1]}"

            # Create base provider data
            provider_data = self._create_provider_data()
            
            # Fetch and process user
            self.logger.info("Fetching user data...")
            user = self.fetch_user()
            
            self.logger.info(f"Processing user: {user.full_name}")
            self.process_user(provider_data, user)
            
            # Push to OAA
            self._push_to_oaa(
                provider_name=provider_name,
                data_source_name=data_source_name,
                provider_data=provider_data
            )
            
        except Exception as e:
            self.logger.error(f"Sync failed: {str(e)}")
            raise

    def _push_to_oaa(self, provider_name: str, data_source_name: str, provider_data: CustomApplication, save_json: bool = False) -> None:
            """Push data to OAA with provider setup."""
            try:
                # Get or create provider
                provider = self.oaa_client.get_provider(provider_name)
                if not provider:
                    self.logger.info(f"Creating new provider: {provider_name}")
                    provider = self.oaa_client.create_provider(
                        name=provider_name,
                        custom_template="application"
                    )
                else:
                    self.logger.info(f"Found existing provider: {provider_name}")

                # Set the icon and push data
                try:
                    self.oaa_client.update_provider_icon(provider['id'], WORKBOARD_ICON_B64)
                    response = self.oaa_client.push_application(
                        provider_name, 
                        data_source_name=data_source_name, 
                        application_object=provider_data, 
                        save_json=save_json
                    )
                    if response.get("warnings", None):
                        self.logger.warning("Push succeeded with warnings:")
                        for e in response["warnings"]:
                            self.logger.warning(e)

                    self.logger.info("Success")

                except OAAClientError as e:
                    self.logger.error(f"Veza API error {e.error}: {e.message} ({e.status_code})")
                    if hasattr(e, "details"):
                        for d in e.details:
                            self.logger.error(d)
                    self.logger.error("Update did not finish")
                    raise e

            except Exception as e:
                self.logger.error(f"Error during provider setup/push: {str(e)}")
                raise

    def _create_provider_data(self) -> CustomApplication:
            """Create and configure the provider data structure."""
            provider_data = CustomApplication(
                name="WorkBoard",
                application_type="Collaboration",
                description="WorkBoard OKR and Strategy Execution Platform"
            )
            
            # Define custom properties
            provider_data.property_definitions.define_local_user_property(
                "workboard_id", 
                OAAPropertyType.STRING
            )
            provider_data.property_definitions.define_local_user_property(
                "email", 
                OAAPropertyType.STRING
            )
            provider_data.property_definitions.define_local_user_property(
                "title", 
                OAAPropertyType.STRING
            )
            provider_data.property_definitions.define_local_user_property(
                "company", 
                OAAPropertyType.STRING
            )
            provider_data.property_definitions.define_local_user_property(
                "manager_id", 
                OAAPropertyType.STRING
            )
            provider_data.property_definitions.define_local_user_property(
                "manager_role", 
                OAAPropertyType.STRING
            )
            provider_data.property_definitions.define_local_user_property(
                "time_zone", 
                OAAPropertyType.STRING
            )
            provider_data.property_definitions.define_local_user_property(
                "external_id", 
                OAAPropertyType.STRING
            )
            
            # Define permissions
            provider_data.add_custom_permission(
                "admin",
                [OAAPermission.DataRead, OAAPermission.DataWrite, 
                OAAPermission.MetadataRead, OAAPermission.MetadataWrite]
            )
            provider_data.add_custom_permission(
                "user",
                [OAAPermission.DataRead, OAAPermission.DataWrite]
            )
            provider_data.add_custom_permission(
                "viewer",
                [OAAPermission.DataRead, OAAPermission.MetadataRead]
            )
            
            return provider_data

    def _push_to_oaa(
        self,
        provider_name: str,
        data_source_name: str,
        provider_data: CustomApplication
    ) -> None:
        """Push provider data to OAA."""
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
    """Main function to run the WorkBoard OAA integration."""
    import argparse
    
    parser = argparse.ArgumentParser(description='WorkBoard OAA Integration')
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set the logging level'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Fetch data but do not push to OAA'
    )
    parser.add_argument(
        '--save-json',
        action='store_true',
        help='Save fetched data to JSON file for debugging'
    )
    args = parser.parse_args()
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    try:
        # Get configurations
        veza_url = get_required_env_var(VEZA_URL)
        veza_api_key = get_required_env_var(VEZA_API_KEY)
        
        # Initialize OAA client
        oaa_client = OAAClient(
            url=veza_url,
            api_key=veza_api_key
        )
        
        # Initialize and run provider
        provider = WorkBoardOAAProvider(oaa_client=oaa_client)
        
        if args.dry_run:
            # Just fetch and display user data
            user = provider.fetch_user()
            logger.info(f"Successfully fetched user data for: {user.full_name}")
            if args.save_json:
                import json
                with open('workboard_user.json', 'w') as f:
                    json.dump({
                        'user_id': user.user_id,
                        'name': user.full_name,
                        'email': user.email,
                        'title': user.get_title(),
                        'company': user.get_company(),
                        'manager': user.manager,
                        'profile': user.profile
                    }, f, indent=2)
                logger.info("Saved user data to workboard_user.json")
        else:
            # Perform full sync
            provider.sync()
        
    except (ConfigurationError, APIError, OAAClientError) as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.debug("Exception details:", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()