import os
import sys
import asyncio
import aiohttp
import json
import csv
import argparse
from datetime import datetime
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
import urllib.parse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
EXPORTS_DIR = "exports"
MAX_LIMIT = 250

def setup_argparse() -> argparse.ArgumentParser:
    """Set up command line argument parser with full help documentation"""
    parser = argparse.ArgumentParser(
        description='Export SailPoint accounts data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Filtering Examples:
-----------------
Single filter:
  --filters "identityId eq \\"2c9180858082150f0180893dbaf44201\\""
  
Multiple filters (use AND):
  --filters "sourceId eq \\"123\\" AND name sw \\"test\\""

Supported filter fields and operators:
- id: eq, in, sw
- identityId: eq, in, sw
- name: eq, in, sw
- nativeIdentity: eq, in, sw
- sourceId: eq, in, sw
- uncorrelated: eq
- entitlements: eq
- origin: eq, in
- manuallyCorrelated: eq
- identity.name: eq, in, sw
- identity.correlated: eq
- identity.identityState: eq, in
- source.displayableName: eq, in
- source.authoritative: eq
- source.connectionType: eq, in

Sorting Examples:
--------------
Single sort:
  --sorters "name"
  
Multiple sorts:
  --sorters "id,name"

Supported sort fields:
id, name, created, modified, sourceId, identityId, identity.id,
nativeIdentity, uuid, manuallyCorrelated, entitlements, origin,
identity.name, identity.identityState, identity.correlated,
source.displayableName, source.authoritative, source.connectionType
""")

    parser.add_argument('--format', 
                       choices=['json', 'csv'], 
                       default='json',
                       help='Output file format (default: json)')
    
    parser.add_argument('--limit', 
                       type=int, 
                       default=250,
                       help=f'Max number of results to return per page (max: {MAX_LIMIT}, default: 250)')
    
    parser.add_argument('--offset', 
                       type=int, 
                       default=0,
                       help='Offset into the full result set (default: 0)')
    
    parser.add_argument('--count', 
                       action='store_true',
                       help='Get total count in response headers (may impact performance)')
    
    parser.add_argument('--filters', 
                       type=str,
                       help='Filter results using the standard syntax (see examples below)')
    
    parser.add_argument('--sorters', 
                       type=str,
                       help='Sort results using comma-separated field names (see examples below)')
    
    parser.add_argument('--output-dir', 
                       type=str,
                       default=EXPORTS_DIR,
                       help=f'Directory for output files (default: {EXPORTS_DIR})')

    return parser

@dataclass
class SailPointConfig:
    """Configuration for SailPoint authentication"""
    tenant: str
    client_id: str
    client_secret: str
    grant_type: str = "client_credentials"
    
    @property
    def token_url(self) -> str:
        """Get the token URL for the tenant"""
        return f"https://{self.tenant}.api.identitynow.com/oauth/token"
    
    @property
    def api_base_url(self) -> str:
        """Get the base API URL"""
        return f"https://{self.tenant}.api.identitynow.com"

class EnvironmentValidator:
    """Validates required environment variables"""
    
    @staticmethod
    def validate() -> SailPointConfig:
        """
        Validates all required environment variables
        Returns: SailPointConfig object
        Raises: ValueError if required variables are missing
        """
        required_vars = {
            'SAILPOINT_TENANT': 'SailPoint tenant name (e.g., "tenant" from tenant.identitynow.com)',
            'SAILPOINT_CLIENT_ID': 'SailPoint OAuth Client ID',
            'SAILPOINT_CLIENT_SECRET': 'SailPoint OAuth Client Secret',
            'SAILPOINT_GRANT_TYPE': 'OAuth grant type (defaults to client_credentials)'
        }
        
        missing = []
        for var, desc in required_vars.items():
            if not os.getenv(var) and var != 'SAILPOINT_GRANT_TYPE':
                missing.append((var, desc))
        
        if missing:
            error_msg = ["Missing required environment variables:"]
            for var, desc in missing:
                error_msg.extend([f"\n{var}:", f"  Description: {desc}"])
            
            error_msg.extend([
                "\nPlease set these environment variables before running the script:",
                "\nmacOS/Linux:"
            ])
            for var, _ in missing:
                error_msg.append(f'export {var}="your-value-here"')
            
            raise ValueError('\n'.join(error_msg))
            
        return SailPointConfig(
            tenant=os.getenv('SAILPOINT_TENANT'),
            client_id=os.getenv('SAILPOINT_CLIENT_ID'),
            client_secret=os.getenv('SAILPOINT_CLIENT_SECRET'),
            grant_type=os.getenv('SAILPOINT_GRANT_TYPE', 'client_credentials')
        )

class SailPointClient:
    def __init__(self, config: SailPointConfig):
        self.config = config
        self.access_token: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        await self.ensure_token()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def ensure_token(self):
        """Get OAuth token using client credentials"""
        if self.session:
            await self.session.close()
            
        async with aiohttp.ClientSession() as session:
            # Prepare form data
            data = aiohttp.FormData()
            data.add_field('grant_type', self.config.grant_type)
            data.add_field('client_id', self.config.client_id)
            data.add_field('client_secret', self.config.client_secret)
            
            headers = {
                'Accept': 'application/json',
                'scope': 'sp:scope:all'
            }
            
            async with session.post(
                self.config.token_url,
                data=data,
                headers=headers,
                ssl=True
            ) as response:
                response.raise_for_status()
                token_data = await response.json()
                self.access_token = token_data['access_token']
                
        # Create new session with token
        self.session = aiohttp.ClientSession(
            headers={
                'Authorization': f'Bearer {self.access_token}',
                'Accept': 'application/json'
            }
        )
    
    async def get_accounts(self, limit: int = 250, offset: int = 0, 
                         count: bool = True, filters: str = None, 
                         sorters: str = None) -> Dict:
        """Get accounts with full query parameter support"""
        params = {
            'limit': min(limit, MAX_LIMIT),
            'offset': offset,
            'count': str(count).lower()
        }
        
        if filters:
            params['filters'] = filters
        
        if sorters:
            params['sorters'] = sorters
            
        url = f"{self.config.api_base_url}/v3/accounts"
        
        async with self.session.get(url, params=params) as response:
            response.raise_for_status()
            items = await response.json()
            return {
                'total': int(response.headers.get('X-Total-Count', len(items))),
                'items': items
            }

def save_to_json(data: List[Dict], filename: str):
    """Save data to JSON file"""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    logger.info(f"Saved JSON data to {filename}")

def save_to_csv(data: List[Dict], filename: str):
    """Save data to CSV file"""
    fieldnames = [
        'id', 
        'name',
        'nativeIdentity',
        'sourceId',
        'identityId',
        'manuallyCorrelated',
        'created',
        'modified',
        'uuid',
        'disabled'
    ]

    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for account in data:
            row = {field: account.get(field, '') for field in fieldnames}
            writer.writerow(row)
    logger.info(f"Saved CSV data to {filename}")

async def main():
    parser = setup_argparse()
    args = parser.parse_args()

    # Validate limit
    if args.limit > MAX_LIMIT:
        logger.warning(f"Limit {args.limit} exceeds maximum of {MAX_LIMIT}. Using {MAX_LIMIT}")
        args.limit = MAX_LIMIT

    try:
        # Create exports directory if it doesn't exist
        os.makedirs(args.output_dir, exist_ok=True)

        # Validate environment and get config
        config = EnvironmentValidator.validate()
        
        # Initialize client
        async with SailPointClient(config) as client:
            offset = args.offset
            all_accounts = []
            
            # Get first batch
            result = await client.get_accounts(
                limit=args.limit,
                offset=offset,
                count=args.count,
                filters=args.filters,
                sorters=args.sorters
            )
            
            current_batch = result['items']
            all_accounts.extend(current_batch)
            logger.info(f"Retrieved {len(current_batch)} accounts")
            
            # Fetch remaining pages if there are more items
            while len(current_batch) == args.limit:  # If we got a full page, there might be more
                offset += args.limit
                result = await client.get_accounts(
                    limit=args.limit,
                    offset=offset,
                    count=False,  # No need for count on subsequent pages
                    filters=args.filters,
                    sorters=args.sorters
                )
                current_batch = result['items']
                all_accounts.extend(current_batch)
                logger.info(f"Retrieved {len(all_accounts)} total accounts")
            
            # Only save file if we have results
            if all_accounts:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = os.path.join(args.output_dir, f"sailpoint_accounts_{timestamp}.{args.format}")
                
                if args.format == 'json':
                    save_to_json(all_accounts, filename)
                else:  # csv
                    save_to_csv(all_accounts, filename)
                
                logger.info(f"Export complete. Total accounts retrieved: {len(all_accounts)}")
            else:
                logger.info("No accounts found. No file was created.")
            
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
