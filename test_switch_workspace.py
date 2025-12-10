#!/usr/bin/env python
"""
Test script for switch workspace API with detailed logging.
Run this script to test the switch workspace endpoint and see all middleware logs.
"""
import os
import sys
import django
import logging
import requests
from datetime import datetime

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Configure logging to see all middleware logs
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

# Get logger
logger = logging.getLogger(__name__)

def test_switch_workspace(base_url="http://localhost:8000", token=None, workspace_id=None):
    """
    Test the switch workspace API endpoint.
    
    Args:
        base_url: Base URL of the API
        token: JWT authentication token
        workspace_id: Workspace ID to switch to
    """
    logger.info("=" * 80)
    logger.info("TEST: Switch Workspace API")
    logger.info("=" * 80)
    
    if not token:
        logger.error("JWT token is required. Please provide a valid token.")
        logger.info("Usage: python test_switch_workspace.py <token> <workspace_id>")
        return
    
    if not workspace_id:
        logger.error("Workspace ID is required.")
        logger.info("Usage: python test_switch_workspace.py <token> <workspace_id>")
        return
    
    # Headers
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    
    logger.info(f"Step 1: Preparing request")
    logger.info(f"  - URL: {base_url}/api/v1/workspace/workspaces/{workspace_id}/switch/")
    logger.info(f"  - Method: POST")
    logger.info(f"  - Workspace ID: {workspace_id}")
    logger.info(f"  - Token: {token[:20]}...")
    
    try:
        # Make the request
        logger.info(f"Step 2: Sending POST request to switch workspace")
        response = requests.post(
            f"{base_url}/api/v1/workspace/workspaces/{workspace_id}/switch/",
            headers=headers,
            timeout=10
        )
        
        logger.info(f"Step 3: Response received")
        logger.info(f"  - Status Code: {response.status_code}")
        logger.info(f"  - Response Headers: {dict(response.headers)}")
        
        # Check cookies in response
        if 'Set-Cookie' in response.headers:
            logger.info(f"Step 4: Cookie set in response")
            logger.info(f"  - Set-Cookie header: {response.headers['Set-Cookie']}")
        else:
            logger.warning(f"Step 4: No Set-Cookie header in response")
        
        # Parse response
        try:
            response_data = response.json()
            logger.info(f"Step 5: Response body: {response_data}")
        except:
            logger.warning(f"Step 5: Could not parse response as JSON")
            logger.info(f"  - Response text: {response.text[:200]}")
        
        # Verify cookie
        if 'workspace' in response.cookies:
            cookie_value = response.cookies['workspace']
            logger.info(f"Step 6: Workspace cookie verified")
            logger.info(f"  - Cookie value: {cookie_value}")
            logger.info(f"  - Cookie matches workspace ID: {cookie_value == str(workspace_id)}")
        else:
            logger.warning(f"Step 6: No workspace cookie found in response")
        
        if response.status_code == 200:
            logger.info("=" * 80)
            logger.info("TEST RESULT: SUCCESS")
            logger.info("=" * 80)
        else:
            logger.error("=" * 80)
            logger.error(f"TEST RESULT: FAILED - Status Code: {response.status_code}")
            logger.error("=" * 80)
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {str(e)}")
        logger.error("=" * 80)
        logger.error("TEST RESULT: ERROR")
        logger.error("=" * 80)


def test_get_current_workspace(base_url="http://localhost:8000", token=None):
    """
    Test getting the current workspace after switching.
    """
    logger.info("=" * 80)
    logger.info("TEST: Get Current Workspace API")
    logger.info("=" * 80)
    
    if not token:
        logger.error("JWT token is required.")
        return
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    
    try:
        logger.info(f"Step 1: Getting current workspace")
        response = requests.get(
            f"{base_url}/api/v1/workspace/workspaces/current/",
            headers=headers,
            timeout=10
        )
        
        logger.info(f"Step 2: Response received - Status: {response.status_code}")
        if response.status_code == 200:
            workspace_data = response.json()
            logger.info(f"Step 3: Current workspace: {workspace_data}")
        else:
            logger.warning(f"Step 3: Failed to get current workspace - {response.text}")
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {str(e)}")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python test_switch_workspace.py <jwt_token> <workspace_id>")
        print("\nExample:")
        print("  python test_switch_workspace.py eyJhbGci... 1")
        sys.exit(1)
    
    token = sys.argv[1]
    workspace_id = sys.argv[2]
    
    # Run tests
    test_switch_workspace(token=token, workspace_id=workspace_id)
    print("\n" + "=" * 80 + "\n")
    test_get_current_workspace(token=token)


