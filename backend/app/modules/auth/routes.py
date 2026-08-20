import urllib.parse
from flask import Blueprint, request, jsonify, redirect, current_app, make_response, g
from app.modules.auth.schemas import (
    validate_register_input,
    validate_login_input,
    validate_forgot_password_input,
    validate_reset_password_input
)
from app.modules.auth.service import AuthService
from app.modules.auth.security import login_required, extract_auth_token, verify_access_token
from models.user import User

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    is_valid, err_msg = validate_register_input(data)
    if not is_valid:
        return jsonify({'authenticated': False, 'message': err_msg}), 400

    name = data.get('full_name') or data.get('name')
    email = data.get('email')
    password = data.get('password')

    result, err = AuthService.register_user(name, email, password)
    if err:
        return jsonify({'authenticated': False, 'message': err}), 400

    resp = make_response(jsonify(result), 201)
    resp.set_cookie('access_token', result['access_token'], httponly=True, samesite='Lax', max_age=86400)
    resp.set_cookie('refresh_token', result['refresh_token'], httponly=True, samesite='Lax', max_age=604800)
    return resp

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    is_valid, err_msg = validate_login_input(data)
    if not is_valid:
        return jsonify({'authenticated': False, 'message': err_msg}), 400

    email = data.get('email')
    password = data.get('password')

    result, err = AuthService.authenticate_user(email, password)
    if err:
        return jsonify({'authenticated': False, 'message': err}), 401

    resp = make_response(jsonify(result), 200)
    resp.set_cookie('access_token', result['access_token'], httponly=True, samesite='Lax', max_age=86400)
    resp.set_cookie('refresh_token', result['refresh_token'], httponly=True, samesite='Lax', max_age=604800)
    return resp

@auth_bp.route('/logout', methods=['POST'])
def logout():
    refresh_token = request.cookies.get('refresh_token') or (request.get_json() or {}).get('refresh_token')
    AuthService.revoke_session(refresh_token)

    resp = make_response(jsonify({'authenticated': False, 'message': 'Logged out successfully'}), 200)
    resp.set_cookie('access_token', '', expires=0)
    resp.set_cookie('refresh_token', '', expires=0)
    return resp

@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    data = request.get_json() or {}
    refresh_token = data.get('refresh_token') or request.cookies.get('refresh_token')
    
    if not refresh_token:
        return jsonify({'authenticated': False, 'message': 'Refresh token missing'}), 401

    result, err = AuthService.refresh_session(refresh_token)
    if err:
        return jsonify({'authenticated': False, 'message': err}), 401

    resp = make_response(jsonify(result), 200)
    resp.set_cookie('access_token', result['access_token'], httponly=True, samesite='Lax', max_age=86400)
    resp.set_cookie('refresh_token', result['refresh_token'], httponly=True, samesite='Lax', max_age=604800)
    return resp

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json() or {}
    is_valid, err_msg = validate_forgot_password_input(data)
    if not is_valid:
        return jsonify({'message': err_msg}), 400

    msg = AuthService.create_password_reset_request(data.get('email'))
    return jsonify({'message': msg}), 200

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json() or {}
    is_valid, err_msg = validate_reset_password_input(data)
    if not is_valid:
        return jsonify({'message': err_msg}), 400

    success, msg = AuthService.reset_password_with_token(data.get('token'), data.get('password'))
    if not success:
        return jsonify({'message': msg}), 400

    return jsonify({'message': msg}), 200

@auth_bp.route('/me', methods=['GET'])
@login_required
def get_me():
    user = g.current_user
    return jsonify({
        'authenticated': True,
        'user': user.to_dict()
    }), 200

@auth_bp.route('/google', methods=['GET'])
def google_auth_redirect():
    client_id = current_app.config.get('GOOGLE_CLIENT_ID')
    redirect_uri = current_app.config.get('GOOGLE_REDIRECT_URI')

    if client_id == 'mock-google-client-id':
        mock_code = 'mock_oauth_code_12345'
        return redirect(f"{redirect_uri}?code={mock_code}")

    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile',
        'prompt': 'select_account'
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return redirect(url)

@auth_bp.route('/google/callback', methods=['GET', 'POST'])
def google_callback():
    code = request.args.get('code')
    data = request.get_json() if request.is_json else {}
    mock_info = data.get('mock_user')

    if not code and not mock_info and request.args.get('mock') == '1':
        mock_info = {
            'email': 'google.user@example.com',
            'name': 'Google Account User',
            'picture': 'https://lh3.googleusercontent.com/a/default-user'
        }

    result, err = AuthService.handle_google_oauth(code=code, mock_info=mock_info)
    if err:
        return jsonify({'authenticated': False, 'message': err}), 400

    # If JSON API request
    if request.headers.get('Accept') == 'application/json' or request.is_json:
        resp = make_response(jsonify(result), 200)
        resp.set_cookie('access_token', result['access_token'], httponly=True, samesite='Lax', max_age=86400)
        resp.set_cookie('refresh_token', result['refresh_token'], httponly=True, samesite='Lax', max_age=604800)
        return resp

    # Browser redirect callback flow -> redirect to frontend with token param or set cookie
    frontend_url = current_app.config.get('FRONTEND_URL')
    if not frontend_url or frontend_url == '*' or (isinstance(frontend_url, str) and frontend_url.startswith('^')):
        cors_origins = current_app.config.get('CORS_ORIGINS')
        if isinstance(cors_origins, list) and cors_origins:
            valid_origins = [o for o in cors_origins if isinstance(o, str) and o and o != '*' and not o.startswith('^')]
            frontend_url = valid_origins[0] if valid_origins else 'http://localhost:5173'
        elif isinstance(cors_origins, str) and cors_origins != '*' and not cors_origins.startswith('^'):
            frontend_url = cors_origins.split(',')[0].strip()
        else:
            frontend_url = 'http://localhost:5173'

    frontend_url = frontend_url.rstrip('/')
    
    redirect_target = f"{frontend_url}/login?token={result['access_token']}&refresh_token={result['refresh_token']}"
    resp = make_response(redirect(redirect_target))
    resp.set_cookie('access_token', result['access_token'], httponly=True, samesite='Lax', max_age=86400)
    resp.set_cookie('refresh_token', result['refresh_token'], httponly=True, samesite='Lax', max_age=604800)
    return resp
