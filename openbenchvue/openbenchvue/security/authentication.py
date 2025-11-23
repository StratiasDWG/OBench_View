"""
Authentication System for OpenBenchVue

Provides user authentication with password hashing and token-based sessions.
"""

import hashlib
import secrets
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependency
_audit_logger = None

def _get_audit_logger():
    """Lazy load audit logger to avoid circular imports"""
    global _audit_logger
    if _audit_logger is None:
        try:
            from .audit import audit_logger
            _audit_logger = audit_logger
        except ImportError:
            _audit_logger = None
    return _audit_logger


@dataclass
class User:
    """Represents a user"""
    username: str
    password_hash: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary (without password hash)"""
        return {
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'roles': self.roles,
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
        }


@dataclass
class Token:
    """Represents an authentication token"""
    token: str
    username: str
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    metadata: Dict = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if token is expired"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    def is_valid(self) -> bool:
        """Check if token is valid"""
        return not self.is_expired()


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """
    Hash a password using PBKDF2-HMAC-SHA256

    Args:
        password: Plain text password
        salt: Optional salt (generated if not provided)

    Returns:
        Hashed password in format: salt$hash
    """
    if salt is None:
        salt = secrets.token_hex(16)

    # Use PBKDF2 with 100,000 iterations
    password_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )

    return f"{salt}${password_hash.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against a hash

    Args:
        password: Plain text password
        password_hash: Hashed password in format: salt$hash

    Returns:
        True if password matches, False otherwise
    """
    try:
        salt, expected_hash = password_hash.split('$', 1)
        computed_hash = hash_password(password, salt)
        return secrets.compare_digest(computed_hash, password_hash)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


class AuthenticationManager:
    """
    Manages user authentication

    Handles user registration, login, logout, and token management.
    """

    def __init__(
        self,
        token_expiry_hours: int = 24,
        max_login_attempts: int = 5,
        lockout_duration_minutes: int = 30,
    ):
        """
        Initialize authentication manager

        Args:
            token_expiry_hours: Token expiration time in hours
            max_login_attempts: Maximum failed login attempts before lockout
            lockout_duration_minutes: Lockout duration in minutes
        """
        self.token_expiry_hours = token_expiry_hours
        self.max_login_attempts = max_login_attempts
        self.lockout_duration_minutes = lockout_duration_minutes

        self._users: Dict[str, User] = {}
        self._tokens: Dict[str, Token] = {}
        self._login_attempts: Dict[str, List[float]] = {}

        # Create default admin user
        self._create_default_admin()

    def _create_default_admin(self):
        """Create default admin user with secure random password"""
        # Generate secure random password
        temp_password = secrets.token_urlsafe(16)

        admin = User(
            username='admin',
            password_hash=hash_password(temp_password),
            email='admin@openbenchvue.local',
            full_name='Administrator',
            roles=['admin', 'user'],
        )
        self._users['admin'] = admin

        # Log the temporary password securely
        logger.critical(
            "\n" + "=" * 80 + "\n"
            "DEFAULT ADMIN USER CREATED\n"
            f"Username: admin\n"
            f"Temporary Password: {temp_password}\n"
            "\n"
            "⚠️  IMPORTANT: Change this password immediately after first login!\n"
            "⚠️  This password will not be shown again.\n"
            "=" * 80
        )

    def register_user(
        self,
        username: str,
        password: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        roles: Optional[List[str]] = None,
    ) -> bool:
        """
        Register a new user

        Args:
            username: Username
            password: Plain text password (will be hashed)
            email: User email
            full_name: User's full name
            roles: List of roles

        Returns:
            True if registration succeeded, False otherwise
        """
        audit = _get_audit_logger()

        if username in self._users:
            logger.warning(f"User {username} already exists")
            if audit:
                audit.log_authentication('register', username, result='failure',
                                        reason='username_already_exists')
            return False

        # Validate password strength
        if not self._validate_password_strength(password):
            logger.warning("Password does not meet strength requirements")
            if audit:
                audit.log_authentication('register', username, result='failure',
                                        reason='weak_password')
            return False

        user = User(
            username=username,
            password_hash=hash_password(password),
            email=email,
            full_name=full_name,
            roles=roles or ['user'],
        )

        self._users[username] = user
        logger.info(f"Registered user: {username}")

        if audit:
            audit.log_authentication('register', username, result='success',
                                    email=email, roles=roles or ['user'])

        return True

    def login(self, username: str, password: str, ip_address: Optional[str] = None) -> Optional[Token]:
        """
        Authenticate user and create token

        Args:
            username: Username
            password: Plain text password
            ip_address: IP address of the user (for audit logging)

        Returns:
            Token if authentication succeeded, None otherwise
        """
        audit = _get_audit_logger()

        # Check if account is locked
        if self._is_locked_out(username):
            logger.warning(f"Account {username} is locked out")
            if audit:
                audit.log_authentication('login', username, result='failure',
                                        reason='account_locked', ip_address=ip_address)
            return None

        # Get user
        user = self._users.get(username)
        if user is None or not user.enabled:
            self._record_failed_attempt(username)
            logger.warning(f"Login failed: user {username} not found or disabled")
            if audit:
                audit.log_authentication('login', username, result='failure',
                                        reason='user_not_found_or_disabled',
                                        ip_address=ip_address)
            return None

        # Verify password
        if not verify_password(password, user.password_hash):
            self._record_failed_attempt(username)
            logger.warning(f"Login failed: invalid password for {username}")
            if audit:
                audit.log_authentication('login', username, result='failure',
                                        reason='invalid_password', ip_address=ip_address)
            return None

        # Clear failed attempts
        self._login_attempts.pop(username, None)

        # Update last login
        user.last_login = datetime.now()

        # Create token
        token = Token(
            token=secrets.token_urlsafe(32),
            username=username,
            expires_at=datetime.now() + timedelta(hours=self.token_expiry_hours),
        )

        self._tokens[token.token] = token
        logger.info(f"User {username} logged in")

        if audit:
            audit.log_authentication('login', username, result='success',
                                    ip_address=ip_address)

        return token

    def logout(self, token_str: str) -> bool:
        """
        Logout user and invalidate token

        Args:
            token_str: Token string

        Returns:
            True if logout succeeded
        """
        audit = _get_audit_logger()

        if token_str in self._tokens:
            username = self._tokens[token_str].username
            del self._tokens[token_str]
            logger.info(f"User {username} logged out")

            if audit:
                audit.log_authentication('logout', username, result='success')

            return True

        if audit:
            audit.log_authentication('logout', 'unknown', result='failure',
                                    reason='invalid_token')

        return False

    def validate_token(self, token_str: str) -> Optional[User]:
        """
        Validate token and return user

        Args:
            token_str: Token string

        Returns:
            User if token is valid, None otherwise
        """
        token = self._tokens.get(token_str)
        if token is None:
            return None

        if token.is_expired():
            del self._tokens[token_str]
            logger.info(f"Token expired for {token.username}")
            return None

        user = self._users.get(token.username)
        if user is None or not user.enabled:
            return None

        return user

    def change_password(
        self,
        username: str,
        old_password: str,
        new_password: str
    ) -> bool:
        """
        Change user password

        Args:
            username: Username
            old_password: Current password
            new_password: New password

        Returns:
            True if password changed successfully
        """
        user = self._users.get(username)
        if user is None:
            return False

        # Verify old password
        if not verify_password(old_password, user.password_hash):
            logger.warning(f"Password change failed: invalid old password for {username}")
            return False

        # Validate new password
        if not self._validate_password_strength(new_password):
            logger.warning("New password does not meet strength requirements")
            return False

        # Update password
        user.password_hash = hash_password(new_password)
        logger.info(f"Password changed for {username}")

        # Invalidate all tokens for this user
        self._invalidate_user_tokens(username)

        return True

    def delete_user(self, username: str) -> bool:
        """Delete a user"""
        if username in self._users:
            # Invalidate all tokens
            self._invalidate_user_tokens(username)

            del self._users[username]
            logger.info(f"Deleted user: {username}")
            return True
        return False

    def get_user(self, username: str) -> Optional[User]:
        """Get user by username"""
        return self._users.get(username)

    def list_users(self) -> List[User]:
        """List all users"""
        return list(self._users.values())

    def _validate_password_strength(self, password: str) -> bool:
        """
        Validate password meets security requirements

        Requirements:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        """
        if len(password) < 8:
            logger.debug("Password too short (minimum 8 characters)")
            return False

        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?/~`' for c in password)

        if not has_upper:
            logger.debug("Password missing uppercase letter")
        if not has_lower:
            logger.debug("Password missing lowercase letter")
        if not has_digit:
            logger.debug("Password missing digit")
        if not has_special:
            logger.debug("Password missing special character")

        return has_upper and has_lower and has_digit and has_special

    def _is_locked_out(self, username: str) -> bool:
        """Check if account is locked out due to failed attempts"""
        attempts = self._login_attempts.get(username, [])
        if len(attempts) < self.max_login_attempts:
            return False

        # Check if lockout period has expired
        cutoff_time = time.time() - (self.lockout_duration_minutes * 60)
        recent_attempts = [t for t in attempts if t > cutoff_time]

        if len(recent_attempts) >= self.max_login_attempts:
            return True

        # Clear old attempts
        self._login_attempts[username] = recent_attempts
        return False

    def _record_failed_attempt(self, username: str):
        """Record a failed login attempt"""
        if username not in self._login_attempts:
            self._login_attempts[username] = []
        self._login_attempts[username].append(time.time())

    def _invalidate_user_tokens(self, username: str):
        """Invalidate all tokens for a user"""
        tokens_to_remove = [
            token_str for token_str, token in self._tokens.items()
            if token.username == username
        ]
        for token_str in tokens_to_remove:
            del self._tokens[token_str]

    def cleanup_expired_tokens(self):
        """Remove expired tokens"""
        expired = [
            token_str for token_str, token in self._tokens.items()
            if token.is_expired()
        ]
        for token_str in expired:
            del self._tokens[token_str]

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired tokens")
