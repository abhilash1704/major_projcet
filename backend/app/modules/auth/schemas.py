import re

def validate_email_format(email: str) -> bool:
    if not email or not isinstance(email, str):
        return False
    return bool(re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email.strip()))

def validate_register_input(data: dict) -> tuple[bool, str]:
    if not data or not isinstance(data, dict):
        return False, "Invalid request payload"
        
    full_name = data.get('full_name') or data.get('name')
    if not full_name or not str(full_name).strip():
        return False, "Full Name is required"
        
    email = data.get('email')
    if not email or not str(email).strip():
        return False, "Email is required"
    if not validate_email_format(email):
        return False, "Please provide a valid email address"
        
    password = data.get('password')
    if not password:
        return False, "Password is required"
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
        
    confirm_password = data.get('confirm_password') or data.get('confirmPassword')
    if confirm_password is not None and password != confirm_password:
        return False, "Passwords do not match"
        
    return True, None

def validate_login_input(data: dict) -> tuple[bool, str]:
    if not data or not isinstance(data, dict):
        return False, "Invalid request payload"
        
    email = data.get('email')
    if not email or not str(email).strip():
        return False, "Email is required"
    if not validate_email_format(email):
        return False, "Please provide a valid email address"
        
    password = data.get('password')
    if not password:
        return False, "Password is required"
        
    return True, None

def validate_forgot_password_input(data: dict) -> tuple[bool, str]:
    if not data or not isinstance(data, dict):
        return False, "Invalid request payload"
        
    email = data.get('email')
    if not email or not str(email).strip():
        return False, "Email is required"
    if not validate_email_format(email):
        return False, "Please provide a valid email address"
        
    return True, None

def validate_reset_password_input(data: dict) -> tuple[bool, str]:
    if not data or not isinstance(data, dict):
        return False, "Invalid request payload"
        
    token = data.get('token')
    if not token:
        return False, "Reset token is required"
        
    password = data.get('password')
    if not password:
        return False, "New password is required"
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
        
    confirm_password = data.get('confirm_password') or data.get('confirmPassword')
    if confirm_password is not None and password != confirm_password:
        return False, "Passwords do not match"
        
    return True, None
