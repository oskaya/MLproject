"""
Authentication Service
GitHub OAuth integration and user session management
"""
import requests
from functools import wraps
from flask import session, redirect, url_for, request, current_app
from webapp_config import WebAppConfig

def is_authenticated():
    """Check if user is authenticated"""
    return 'github_token' in session and 'user_info' in session

def get_current_user():
    """Get current authenticated user info"""
    if is_authenticated():
        return session.get('user_info')
    return None

def check_user_access(username, access_token, required_org):
    """
    Check if user has access using multiple methods:
    1. Username whitelist
    2. Public organization membership
    """
    from webapp_config import WebAppConfig
    
    print(f"🔍 Checking access for user: {username}")
    
    # Method 1: Username whitelist check
    allowed_users = getattr(WebAppConfig, 'ALLOWED_GITHUB_USERS', [])
    if username in allowed_users:
        print(f"✅ User '{username}' found in whitelist: {allowed_users}")
        return True
    
    print(f"❌ User '{username}' not in whitelist: {allowed_users}")
    
    # Method 2: Public organization membership check
    print(f"🔍 Checking public organization membership...")
    
    return check_github_organization(username, access_token, required_org)

def check_github_organization(username, access_token, required_org):
    """
    Check if user is a member of the required organization using public membership
    """
    print(f"🔍 Checking organization membership for: {username}")
    
    # Use public organization membership endpoint - no special scope required
    org_url = f'https://api.github.com/users/{username}/orgs'
    
    print(f"🔍 Making API request to: {org_url}")
    print(f"🔑 Using authorization header: Authorization: token {access_token[:10]}...")
    
    headers = {
        'Authorization': f'token {access_token}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'Guard-Vision-V2'
    }
    
    try:
        response = requests.get(org_url, headers=headers, timeout=10)
        
        print(f"📡 API Response Status: {response.status_code}")
        print(f"📋 Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            organizations = response.json()
            print(f"🔍 Raw API Response: {organizations}")
            
            org_names = [org['login'] for org in organizations]
            print(f"🏢 User's GitHub Organizations ({len(org_names)} total):")
            
            if org_names:
                for org_name in org_names:
                    print(f"   🏢 {org_name}")
            else:
                print("   📭 No public organizations found")
            
            print(f"🔒 Required organization: '{required_org}'")
            
            # Check if user is member of required organization
            is_member = required_org in org_names
            access_status = "✅ GRANTED" if is_member else "❌ DENIED"
            print(f"🔑 Access: {access_status}")
            
            if not is_member:
                print(f"❌ Access denied for {username}: Not a public member of {required_org}")
                print(f"💡 Note: User might be a private member. Consider using email domain or username whitelist instead.")
            
            return is_member
        else:
            print(f"❌ GitHub API error: {response.status_code}")
            print(f"📄 Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error checking organizations: {e}")
        return False

def get_github_user_info(access_token):
    """
    Get user information from GitHub API
    
    Args:
        access_token: GitHub access token
        
    Returns:
        dict: User information or None if failed
    """
    try:
        headers = {
            'Authorization': f'token {access_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # Get user info
        response = requests.get(
            'https://api.github.com/user',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            user_data = response.json()
            return {
                'id': user_data.get('id'),
                'login': user_data.get('login'),
                'name': user_data.get('name') or user_data.get('login'),
                'email': user_data.get('email'),
                'avatar_url': user_data.get('avatar_url'),
                'html_url': user_data.get('html_url')
            }
        else:
            print(f"❌ Failed to get user info: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ User info error: {e}")
        return None

def login_required(f):
    """
    Decorator to require authentication for routes
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            # Store the original URL to redirect back after login
            session['next_url'] = request.url
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def store_user_session(access_token, user_info):
    """
    Store user session data
    
    Args:
        access_token: GitHub access token
        user_info: User information dict
    """
    session['github_token'] = access_token
    session['user_info'] = user_info
    session.permanent = True
    print(f"✅ User session stored for: {user_info.get('login')}")

def clear_user_session():
    """Clear user session data"""
    session.pop('github_token', None)
    session.pop('user_info', None)
    session.pop('next_url', None)
    print("🧹 User session cleared")

def get_auth_redirect_url():
    """Get URL to redirect to after successful authentication"""
    next_url = session.pop('next_url', None)
    if next_url and next_url != url_for('auth.login'):
        return next_url
    return url_for('main.index')