import requests
from datetime import datetime, timedelta, timezone
from flask import current_app
from database.db import db
from models.user import User
from app.modules.auth.models import RefreshToken, PasswordResetToken
from app.modules.auth.security import hash_password, verify_password, generate_access_token, generate_random_token

class AuthService:
    @staticmethod
    def register_user(name: str, email: str, password: str) -> tuple[dict, str]:
        """Registers a new user with email and password."""
        email_clean = email.strip().lower()
        existing_user = User.query.filter_by(email=email_clean, is_deleted=False).first()
        if existing_user:
            return None, "An account with this email address already exists"
            
        hashed_pwd = hash_password(password)
        
        new_user = User(
            full_name=name.strip(),
            email=email_clean,
            password_hash=hashed_pwd,
            auth_provider='local',
            status='active'
        )
        db.session.add(new_user)
        db.session.commit()
        
        access_token = generate_access_token(new_user.id)
        refresh_token = AuthService.create_refresh_token(new_user.id)
        
        return {
            "authenticated": True,
            "user": new_user.to_dict(),
            "access_token": access_token,
            "refresh_token": refresh_token
        }, None

    @staticmethod
    def authenticate_user(email: str, password: str) -> tuple[dict, str]:
        """Authenticates user with email and password."""
        email_clean = email.strip().lower()
        user = User.query.filter_by(email=email_clean, is_deleted=False).first()
        
        if not user or user.status != 'active':
            return None, "Invalid email or password"
            
        if not user.password_hash or not verify_password(password, user.password_hash):
            return None, "Invalid email or password"
            
        access_token = generate_access_token(user.id)
        refresh_token = AuthService.create_refresh_token(user.id)
        
        return {
            "authenticated": True,
            "user": user.to_dict(),
            "access_token": access_token,
            "refresh_token": refresh_token
        }, None

    @staticmethod
    def create_refresh_token(user_id: str) -> str:
        """Creates and stores a persistent refresh token."""
        token_str = generate_random_token()
        days = current_app.config.get('REFRESH_TOKEN_EXPIRATION_DAYS', 7)
        expires_at = datetime.now(timezone.utc) + timedelta(days=days)
        
        rf = RefreshToken(
            token=token_str,
            user_id=user_id,
            expires_at=expires_at,
            revoked=False
        )
        db.session.add(rf)
        db.session.commit()
        return token_str

    @staticmethod
    def refresh_session(refresh_token_str: str) -> tuple[dict, str]:
        """Validates refresh token and issues a new access token & refresh token."""
        if not refresh_token_str:
            return None, "Refresh token is missing"
            
        rf = RefreshToken.query.filter_by(token=refresh_token_str).first()
        if not rf or not rf.is_valid():
            return None, "Refresh token is invalid or expired"
            
        user = db.session.get(User, rf.user_id)
        if not user or user.is_deleted or user.status != 'active':
            return None, "User account is invalid or inactive"
            
        # Revoke old refresh token & generate new pair
        rf.revoked = True
        new_refresh = AuthService.create_refresh_token(user.id)
        new_access = generate_access_token(user.id)
        
        return {
            "authenticated": True,
            "user": user.to_dict(),
            "access_token": new_access,
            "refresh_token": new_refresh
        }, None

    @staticmethod
    def revoke_session(refresh_token_str: str) -> None:
        """Revokes session refresh token."""
        if refresh_token_str:
            rf = RefreshToken.query.filter_by(token=refresh_token_str).first()
            if rf:
                rf.revoked = True
                db.session.commit()

    @staticmethod
    def create_password_reset_request(email: str) -> str:
        """Creates password reset token for given email. Never throws error if email not found."""
        email_clean = email.strip().lower()
        user = User.query.filter_by(email=email_clean, is_deleted=False).first()
        
        # Always return generic message (do not expose email existence)
        if not user:
            return "If an account with that email exists, a password reset link has been generated."
            
        token_str = generate_random_token()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        prt = PasswordResetToken(
            token=token_str,
            user_id=user.id,
            expires_at=expires_at,
            used=False
        )
        db.session.add(prt)
        db.session.commit()
        
        # In a real environment, send email. Here we return success.
        return "If an account with that email exists, a password reset link has been generated."

    @staticmethod
    def reset_password_with_token(token_str: str, new_password: str) -> tuple[bool, str]:
        """Resets user password using a valid reset token."""
        prt = PasswordResetToken.query.filter_by(token=token_str).first()
        if not prt or not prt.is_valid():
            return False, "Password reset token is invalid or expired"
            
        user = db.session.get(User, prt.user_id)
        if not user or user.is_deleted:
            return False, "Associated user account no longer exists"
            
        user.password_hash = hash_password(new_password)
        prt.used = True
        db.session.commit()
        
        return True, "Password has been reset successfully"

    @staticmethod
    def handle_google_oauth(code: str = None, mock_info: dict = None) -> tuple[dict, str]:
        """Processes Google OAuth authentication."""
        google_name = None
        google_email = None
        google_picture = None

        if mock_info:
            google_name = mock_info.get('name', 'Google User')
            google_email = mock_info.get('email', 'google.user@example.com').lower().strip()
            google_picture = mock_info.get('picture', 'https://lh3.googleusercontent.com/a/default-user')
        elif code:
            client_id = current_app.config.get('GOOGLE_CLIENT_ID')
            client_secret = current_app.config.get('GOOGLE_CLIENT_SECRET')
            redirect_uri = current_app.config.get('GOOGLE_REDIRECT_URI')

            if client_id == 'mock-google-client-id' or not client_secret:
                # Mock fallback for development/testing
                google_email = f"google_user_{code[:6]}@example.com"
                google_name = "Google Test User"
                google_picture = "https://lh3.googleusercontent.com/a/default-user"
            else:
                try:
                    token_res = requests.post("https://oauth2.googleapis.com/token", data={
                        "code": code,
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "redirect_uri": redirect_uri,
                        "grant_type": "authorization_code"
                    }, timeout=10)
                    token_data = token_res.json()
                    access_token = token_data.get("access_token")
                    
                    if not access_token:
                        return None, "Failed to retrieve access token from Google"

                    userinfo_res = requests.get("https://www.googleapis.com/oauth2/v2/userinfo", headers={
                        "Authorization": f"Bearer {access_token}"
                    }, timeout=10)
                    user_info = userinfo_res.json()

                    google_email = user_info.get("email", "").lower().strip()
                    google_name = user_info.get("name", "Google User")
                    google_picture = user_info.get("picture")
                except Exception as exc:
                    return None, f"Google OAuth error: {str(exc)}"

        if not google_email:
            return None, "Could not retrieve user details from Google"

        user = User.query.filter_by(email=google_email, is_deleted=False).first()
        if not user:
            user = User(
                full_name=google_name,
                email=google_email,
                password_hash=None,
                auth_provider='google',
                profile_image=google_picture,
                status='active'
            )
            db.session.add(user)
            db.session.commit()
        else:
            if not user.profile_image and google_picture:
                user.profile_image = google_picture
            if user.auth_provider == 'local':
                user.auth_provider = 'google'
            db.session.commit()

        access_token = generate_access_token(user.id)
        refresh_token = AuthService.create_refresh_token(user.id)

        return {
            "authenticated": True,
            "user": user.to_dict(),
            "access_token": access_token,
            "refresh_token": refresh_token
        }, None
