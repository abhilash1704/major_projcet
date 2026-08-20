import pytest
from app import create_app
from database.db import db
from models.user import User
from app.modules.auth.models import RefreshToken, PasswordResetToken

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "AUTH_SECRET": "test-auth-secret-key-1234567890-32bytes",
        "JWT_EXPIRATION_HOURS": 1,
        "REFRESH_TOKEN_EXPIRATION_DAYS": 1
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_user_registration_success(client):
    res = client.post('/api/auth/register', json={
        "full_name": "Test User",
        "email": "test@example.com",
        "password": "Password123!",
        "confirm_password": "Password123!"
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["authenticated"] is True
    assert data["user"]["email"] == "test@example.com"
    assert data["user"]["name"] == "Test User"
    assert "access_token" in data
    assert "refresh_token" in data

def test_user_registration_duplicate_email(client):
    client.post('/api/auth/register', json={
        "full_name": "User One",
        "email": "duplicate@example.com",
        "password": "Password123!"
    })
    res = client.post('/api/auth/register', json={
        "full_name": "User Two",
        "email": "duplicate@example.com",
        "password": "Password123!"
    })
    assert res.status_code == 400
    data = res.get_json()
    assert data["authenticated"] is False
    assert "already exists" in data["message"]

def test_user_registration_invalid_input(client):
    res = client.post('/api/auth/register', json={
        "full_name": "Test",
        "email": "not-an-email",
        "password": "123"
    })
    assert res.status_code == 400
    data = res.get_json()
    assert "valid email" in data["message"].lower() or "at least 6 characters" in data["message"].lower()

def test_user_login_success(client):
    client.post('/api/auth/register', json={
        "full_name": "Login User",
        "email": "login@example.com",
        "password": "SecretPassword123"
    })
    res = client.post('/api/auth/login', json={
        "email": "login@example.com",
        "password": "SecretPassword123"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["authenticated"] is True
    assert data["user"]["email"] == "login@example.com"
    assert "access_token" in data

def test_user_login_invalid_credentials(client):
    client.post('/api/auth/register', json={
        "full_name": "Login User",
        "email": "login@example.com",
        "password": "SecretPassword123"
    })
    res = client.post('/api/auth/login', json={
        "email": "login@example.com",
        "password": "WrongPassword"
    })
    assert res.status_code == 401
    data = res.get_json()
    assert data["authenticated"] is False
    assert "Invalid email or password" in data["message"]

def test_get_me_authenticated(client):
    reg_res = client.post('/api/auth/register', json={
        "full_name": "Session User",
        "email": "session@example.com",
        "password": "SecretPassword123"
    })
    token = reg_res.get_json()["access_token"]

    res = client.get('/api/auth/me', headers={
        "Authorization": f"Bearer {token}"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["authenticated"] is True
    assert data["user"]["email"] == "session@example.com"

def test_get_me_unauthenticated(client):
    res = client.get('/api/auth/me')
    assert res.status_code == 401
    data = res.get_json()
    assert data["authenticated"] is False

def test_session_refresh(client):
    reg_res = client.post('/api/auth/register', json={
        "full_name": "Refresh User",
        "email": "refresh@example.com",
        "password": "SecretPassword123"
    })
    refresh_token = reg_res.get_json()["refresh_token"]

    res = client.post('/api/auth/refresh', json={
        "refresh_token": refresh_token
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["authenticated"] is True
    assert "access_token" in data
    assert "refresh_token" in data

def test_logout_revocation(client):
    reg_res = client.post('/api/auth/register', json={
        "full_name": "Logout User",
        "email": "logout@example.com",
        "password": "SecretPassword123"
    })
    refresh_token = reg_res.get_json()["refresh_token"]

    client.post('/api/auth/logout', json={
        "refresh_token": refresh_token
    })

    # Try refreshing session with revoked token
    res = client.post('/api/auth/refresh', json={
        "refresh_token": refresh_token
    })
    assert res.status_code == 401
    data = res.get_json()
    assert "invalid or expired" in data["message"].lower()

def test_forgot_and_reset_password(client):
    client.post('/api/auth/register', json={
        "full_name": "Reset User",
        "email": "reset@example.com",
        "password": "OldPassword123"
    })

    # Request reset token
    res = client.post('/api/auth/forgot-password', json={
        "email": "reset@example.com"
    })
    assert res.status_code == 200

    # Retrieve token directly from DB for test assertion
    with client.application.app_context():
        user = User.query.filter_by(email="reset@example.com").first()
        token_obj = PasswordResetToken.query.filter_by(user_id=user.id).first()
        token_str = token_obj.token

    # Reset password
    res_reset = client.post('/api/auth/reset-password', json={
        "token": token_str,
        "password": "NewPassword123",
        "confirm_password": "NewPassword123"
    })
    assert res_reset.status_code == 200

    # Attempt login with new password
    res_login = client.post('/api/auth/login', json={
        "email": "reset@example.com",
        "password": "NewPassword123"
    })
    assert res_login.status_code == 200
    assert res_login.get_json()["authenticated"] is True

def test_google_oauth_mock_flow(client):
    res = client.get('/api/auth/google/callback?mock=1', headers={
        "Accept": "application/json"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["authenticated"] is True
    assert data["user"]["email"] == "google.user@example.com"
    assert data["user"]["provider"] == "google"

def test_google_oauth_browser_redirect_flow(client):
    res = client.get('/api/auth/google/callback?code=mock_oauth_code_12345')
    assert res.status_code == 302
    assert res.headers["Location"].startswith("http://localhost:5173/login?token=")
    assert "refresh_token=" in res.headers["Location"]

