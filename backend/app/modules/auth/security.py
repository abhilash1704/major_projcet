import jwt
import bcrypt
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import request, jsonify, current_app, g
from database.db import db
from models.user import User

def hash_password(password: str) -> str:
    """Hashes password using bcrypt."""
    if not password:
        raise ValueError("Password cannot be empty")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, password_hash: str) -> bool:
    """Verifies password against bcrypt hash."""
    if not password or not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False

def get_auth_secret() -> str:
    secret = current_app.config.get('AUTH_SECRET') or current_app.config.get('SECRET_KEY') or 'default-auth-secret-key-min-32-bytes'
    if len(secret) < 32:
        secret = secret.ljust(32, '0')
    return secret

def generate_access_token(user_id: str, expires_in_hours: int = 24) -> str:
    """Generates signed JWT access token."""
    now = datetime.now(timezone.utc)
    payload = {
        'sub': user_id,
        'iat': int(now.timestamp()),
        'exp': int((now + timedelta(hours=expires_in_hours)).timestamp()),
        'type': 'access'
    }
    return jwt.encode(payload, get_auth_secret(), algorithm='HS256')

def verify_access_token(token: str) -> dict:
    """Decodes and validates JWT access token."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, get_auth_secret(), algorithms=['HS256'])
        if payload.get('type') != 'access':
            return None
        return payload
    except Exception:
        return None

def generate_random_token() -> str:
    """Generates secure random string for refresh & reset tokens."""
    return secrets.token_urlsafe(32)

def extract_auth_token() -> str:
    """Extracts JWT token from Authorization header or cookies."""
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header.split(' ', 1)[1].strip()
    
    cookie_token = request.cookies.get('access_token')
    if cookie_token:
        return cookie_token.strip()
        
    return None

def login_required(f):
    """Decorator requiring valid authenticated JWT session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = extract_auth_token()
        if not token:
            return jsonify({'authenticated': False, 'message': 'Authentication token is missing'}), 401
            
        payload = verify_access_token(token)
        if not payload:
            return jsonify({'authenticated': False, 'message': 'Token is invalid or expired'}), 401
            
        user_id = payload.get('sub')
        user = db.session.get(User, user_id)
        if not user or user.is_deleted or user.status != 'active':
            return jsonify({'authenticated': False, 'message': 'User not found or account inactive'}), 401
            
        g.current_user = user
        return f(*args, **kwargs)
    return decorated
