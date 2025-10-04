"""
Authentication Routes
Login, logout, and OAuth callback handling
"""
import os
import secrets
import requests
from urllib.parse import urlencode
from flask import Blueprint, redirect, url_for, flash, render_template, request, session
from webapp_config import WebAppConfig
from app.services import auth_service

# Allow HTTP for development (disable SSL requirement)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Create auth blueprint
bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/login')
def login():
    """Show login page"""
    if auth_service.is_authenticated():
        return redirect(url_for('main.index'))
    return render_template('login.html')

@bp.route('/github')
def github_login():
    """Initiate GitHub OAuth login"""
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    session['github_state'] = state
    
    # GitHub OAuth parameters
    params = {
        'client_id': WebAppConfig.GITHUB_CLIENT_ID,
        'redirect_uri': url_for('auth.github_callback', _external=True),
        'scope': WebAppConfig.GITHUB_OAUTH_SCOPE,
        'state': state,
        'allow_signup': 'false'
    }
    
    github_auth_url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"
    return redirect(github_auth_url)

@bp.route('/callback')
def github_callback():
    """Handle GitHub OAuth callback"""
    try:
        # Verify state for CSRF protection
        if request.args.get('state') != session.get('github_state'):
            flash('Invalid state parameter. Please try again.', 'error')
            return redirect(url_for('auth.login'))
        
        # Get authorization code
        code = request.args.get('code')
        if not code:
            error = request.args.get('error', 'Unknown error')
            flash(f'GitHub authorization failed: {error}', 'error')
            return redirect(url_for('auth.login'))
        
        # Exchange code for access token
        token_data = {
            'client_id': WebAppConfig.GITHUB_CLIENT_ID,
            'client_secret': WebAppConfig.GITHUB_CLIENT_SECRET,
            'code': code,
            'redirect_uri': url_for('auth.github_callback', _external=True)
        }
        
        headers = {'Accept': 'application/json'}
        token_response = requests.post(
            'https://github.com/login/oauth/access_token',
            data=token_data,
            headers=headers,
            timeout=10
        )
        
        if token_response.status_code != 200:
            flash('Failed to obtain access token from GitHub.', 'error')
            return redirect(url_for('auth.login'))
        
        token_json = token_response.json()
        access_token = token_json.get('access_token')
        
        if not access_token:
            error_description = token_json.get('error_description', 'Unknown error')
            flash(f'GitHub token error: {error_description}', 'error')
            return redirect(url_for('auth.login'))
        
        print(f"🔑 GitHub access token obtained")
        
        # Get user information
        user_info = auth_service.get_github_user_info(access_token)
        if not user_info:
            flash('Failed to get user information from GitHub.', 'error')
            return redirect(url_for('auth.login'))
        
        print(f"👤 User info obtained: {user_info.get('login')} ({user_info.get('name', 'No name')})")
        print(f"📧 User email: {user_info.get('email', 'No public email')}")
        
        # Check user access (whitelist or organization membership)
        print(f"\n🔍 Checking access for: {user_info.get('login')}")
        username = user_info.get('login')
        if not auth_service.check_user_access(username, access_token, WebAppConfig.ALLOWED_GITHUB_ORG):
            print(f"❌ Access denied for {user_info.get('login')}")
            flash(f'Access denied. Contact administrator for access.', 'error')
            return redirect(url_for('auth.login'))
        
        print(f"✅ Organization access granted for: {user_info.get('login')}")
        print(f"🎉 Welcome {user_info.get('name', user_info.get('login'))}!")
        
        # Store user session
        auth_service.store_user_session(access_token, user_info)
        
        flash(f'Welcome, {user_info.get("name")}!', 'success')
        
        # Clean up state
        session.pop('github_state', None)
        
        # Redirect to original URL or home
        return redirect(auth_service.get_auth_redirect_url())
        
    except Exception as e:
        print(f"❌ Login error: {e}")
        flash('Login failed due to an unexpected error.', 'error')
        return redirect(url_for('auth.login'))

@bp.route('/logout')
def logout():
    """Logout user and clear session"""
    user = auth_service.get_current_user()
    username = user.get('login') if user else 'User'
    
    auth_service.clear_user_session()
    
    flash(f'Goodbye, {username}!', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/profile')
@auth_service.login_required
def profile():
    """Show user profile (for debugging)"""
    user = auth_service.get_current_user()
    return {
        'user': user,
        'authenticated': auth_service.is_authenticated()
    }