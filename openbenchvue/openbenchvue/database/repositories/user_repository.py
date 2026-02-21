"""
User Repository

Data access layer for user management.
"""

import logging
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session, joinedload

from ..models import UserModel, RoleModel, UserRoleModel, TokenModel, APIKeyModel
from .base import BaseRepository

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository[UserModel]):
    """Repository for user operations"""

    def __init__(self, session: Session):
        super().__init__(UserModel, session)

    def get_by_username(self, username: str) -> Optional[UserModel]:
        """Get user by username"""
        return self.session.query(UserModel).filter_by(username=username).first()

    def get_by_email(self, email: str) -> Optional[UserModel]:
        """Get user by email"""
        return self.session.query(UserModel).filter_by(email=email).first()

    def get_with_roles(self, user_id: int) -> Optional[UserModel]:
        """Get user with loaded roles"""
        return self.session.query(UserModel).options(
            joinedload(UserModel.roles).joinedload(UserRoleModel.role)
        ).filter_by(id=user_id).first()

    def get_active_users(self) -> List[UserModel]:
        """Get all active users"""
        return self.session.query(UserModel).filter_by(is_active=True).all()

    def increment_failed_login(self, user_id: int) -> bool:
        """Increment failed login attempts"""
        user = self.get_by_id(user_id)
        if user:
            user.failed_login_attempts += 1
            self.session.flush()
            return True
        return False

    def reset_failed_login(self, user_id: int) -> bool:
        """Reset failed login attempts to zero"""
        user = self.get_by_id(user_id)
        if user:
            user.failed_login_attempts = 0
            user.is_locked = False
            self.session.flush()
            return True
        return False

    def lock_account(self, user_id: int) -> bool:
        """Lock user account"""
        user = self.get_by_id(user_id)
        if user:
            user.is_locked = True
            self.session.flush()
            logger.warning(f"Account locked for user ID {user_id}")
            return True
        return False

    def unlock_account(self, user_id: int) -> bool:
        """Unlock user account"""
        user = self.get_by_id(user_id)
        if user:
            user.is_locked = False
            user.failed_login_attempts = 0
            self.session.flush()
            logger.info(f"Account unlocked for user ID {user_id}")
            return True
        return False

    def update_last_login(self, user_id: int) -> bool:
        """Update last login timestamp"""
        user = self.get_by_id(user_id)
        if user:
            user.last_login = datetime.utcnow()
            self.session.flush()
            return True
        return False

    def add_role(self, user_id: int, role_id: int, assigned_by: Optional[str] = None) -> bool:
        """Add role to user"""
        try:
            # Check if already exists
            existing = self.session.query(UserRoleModel).filter_by(
                user_id=user_id, role_id=role_id
            ).first()

            if existing:
                logger.warning(f"User {user_id} already has role {role_id}")
                return False

            user_role = UserRoleModel(
                user_id=user_id,
                role_id=role_id,
                assigned_by=assigned_by
            )
            self.session.add(user_role)
            self.session.flush()
            logger.info(f"Added role {role_id} to user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error adding role to user: {e}")
            return False

    def remove_role(self, user_id: int, role_id: int) -> bool:
        """Remove role from user"""
        try:
            user_role = self.session.query(UserRoleModel).filter_by(
                user_id=user_id, role_id=role_id
            ).first()

            if not user_role:
                logger.warning(f"User {user_id} doesn't have role {role_id}")
                return False

            self.session.delete(user_role)
            self.session.flush()
            logger.info(f"Removed role {role_id} from user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error removing role from user: {e}")
            return False

    def get_user_roles(self, user_id: int) -> List[RoleModel]:
        """Get all roles for a user"""
        user = self.get_with_roles(user_id)
        if user:
            return [ur.role for ur in user.roles]
        return []


class TokenRepository(BaseRepository[TokenModel]):
    """Repository for authentication tokens"""

    def __init__(self, session: Session):
        super().__init__(TokenModel, session)

    def get_by_token(self, token: str) -> Optional[TokenModel]:
        """Get token by token string"""
        return self.session.query(TokenModel).filter_by(token=token).first()

    def get_by_refresh_token(self, refresh_token: str) -> Optional[TokenModel]:
        """Get token by refresh token"""
        return self.session.query(TokenModel).filter_by(refresh_token=refresh_token).first()

    def get_user_tokens(self, user_id: int) -> List[TokenModel]:
        """Get all tokens for a user"""
        return self.session.query(TokenModel).filter_by(user_id=user_id).all()

    def revoke_token(self, token: str) -> bool:
        """Revoke (delete) a token"""
        token_obj = self.get_by_token(token)
        if token_obj:
            self.session.delete(token_obj)
            self.session.flush()
            return True
        return False

    def revoke_user_tokens(self, user_id: int) -> int:
        """Revoke all tokens for a user"""
        count = self.session.query(TokenModel).filter_by(user_id=user_id).delete()
        self.session.flush()
        logger.info(f"Revoked {count} tokens for user {user_id}")
        return count

    def cleanup_expired_tokens(self) -> int:
        """Delete expired tokens"""
        count = self.session.query(TokenModel).filter(
            TokenModel.expires_at < datetime.utcnow()
        ).delete()
        self.session.flush()
        logger.info(f"Cleaned up {count} expired tokens")
        return count

    def update_last_used(self, token: str) -> bool:
        """Update last used timestamp"""
        token_obj = self.get_by_token(token)
        if token_obj:
            token_obj.last_used_at = datetime.utcnow()
            self.session.flush()
            return True
        return False


class RoleRepository(BaseRepository[RoleModel]):
    """Repository for roles"""

    def __init__(self, session: Session):
        super().__init__(RoleModel, session)

    def get_by_name(self, name: str) -> Optional[RoleModel]:
        """Get role by name"""
        return self.session.query(RoleModel).filter_by(name=name).first()

    def get_or_create(self, name: str, description: str, permissions: List[str]) -> RoleModel:
        """Get existing role or create new one"""
        role = self.get_by_name(name)
        if role:
            return role

        role = RoleModel(
            name=name,
            description=description,
            permissions=permissions
        )
        self.session.add(role)
        self.session.flush()
        logger.info(f"Created role: {name}")
        return role


class APIKeyRepository(BaseRepository[APIKeyModel]):
    """Repository for API keys"""

    def __init__(self, session: Session):
        super().__init__(APIKeyModel, session)

    def get_by_key_hash(self, key_hash: str) -> Optional[APIKeyModel]:
        """Get API key by hash"""
        return self.session.query(APIKeyModel).filter_by(key_hash=key_hash).first()

    def get_user_keys(self, user_id: int, active_only: bool = True) -> List[APIKeyModel]:
        """Get all API keys for a user"""
        query = self.session.query(APIKeyModel).filter_by(user_id=user_id)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.all()

    def revoke_key(self, key_id: int) -> bool:
        """Revoke (deactivate) an API key"""
        key = self.get_by_id(key_id)
        if key:
            key.is_active = False
            self.session.flush()
            logger.info(f"Revoked API key ID {key_id}")
            return True
        return False

    def update_last_used(self, key_id: int) -> bool:
        """Update last used timestamp"""
        key = self.get_by_id(key_id)
        if key:
            key.last_used_at = datetime.utcnow()
            self.session.flush()
            return True
        return False

    def cleanup_expired_keys(self) -> int:
        """Deactivate expired API keys"""
        count = self.session.query(APIKeyModel).filter(
            APIKeyModel.expires_at < datetime.utcnow(),
            APIKeyModel.is_active == True
        ).update({'is_active': False})
        self.session.flush()
        logger.info(f"Deactivated {count} expired API keys")
        return count
