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

def check_github_organization(access_token, required_org):
    """
    Check if user is member of required GitHub organization
    
    Args:
        access_token: GitHub access token
        required_org: Required organization name
        
    Returns:
        bool: True if user is member of organization
    """
    try:
        headers = {
            'Authorization': f'token {access_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # Get user's organizations
        response = requests.get(
            'https://api.github.com/user/orgs',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            orgs = response.json()
            user_orgs = [org['login'] for org in orgs]
            print(f"🏢 User organizations: {user_orgs}")
            return required_org in user_orgs
        else:
            print(f"❌ Failed to get organizations: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Organization check error: {e}")
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
    """Get URL to redirect after successful authentication"""
    next_url = session.pop('next_url', None)
    return next_url or url_for('main.index')