"""
Authorization and Role-Based Access Control

Manages permissions and roles for access control.
"""

from dataclasses import dataclass, field
from typing import Set, Dict, List, Callable, Optional
from functools import wraps
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Permission(Enum):
    """System permissions"""
    # Instrument permissions
    INSTRUMENT_VIEW = 'instrument:view'
    INSTRUMENT_CONNECT = 'instrument:connect'
    INSTRUMENT_CONTROL = 'instrument:control'
    INSTRUMENT_CONFIGURE = 'instrument:configure'

    # Data permissions
    DATA_VIEW = 'data:view'
    DATA_EXPORT = 'data:export'
    DATA_DELETE = 'data:delete'

    # Automation permissions
    AUTOMATION_VIEW = 'automation:view'
    AUTOMATION_CREATE = 'automation:create'
    AUTOMATION_EXECUTE = 'automation:execute'
    AUTOMATION_DELETE = 'automation:delete'

    # System permissions
    SYSTEM_CONFIGURE = 'system:configure'
    USER_MANAGE = 'user:manage'
    PLUGIN_MANAGE = 'plugin:manage'


@dataclass
class Role:
    """Represents a role with permissions"""
    name: str
    permissions: Set[Permission] = field(default_factory=set)
    description: str = ""

    def has_permission(self, permission: Permission) -> bool:
        """Check if role has a permission"""
        return permission in self.permissions

    def add_permission(self, permission: Permission):
        """Add a permission to the role"""
        self.permissions.add(permission)

    def remove_permission(self, permission: Permission):
        """Remove a permission from the role"""
        self.permissions.discard(permission)


class AuthorizationManager:
    """
    Manages roles and permissions

    Implements role-based access control (RBAC).
    """

    def __init__(self):
        self._roles: Dict[str, Role] = {}
        self._create_default_roles()

    def _create_default_roles(self):
        """Create default system roles"""
        # Admin role: all permissions
        admin = Role(
            name='admin',
            permissions=set(Permission),
            description='Administrator with full access'
        )
        self._roles['admin'] = admin

        # User role: basic permissions
        user = Role(
            name='user',
            permissions={
                Permission.INSTRUMENT_VIEW,
                Permission.INSTRUMENT_CONNECT,
                Permission.INSTRUMENT_CONTROL,
                Permission.DATA_VIEW,
                Permission.DATA_EXPORT,
                Permission.AUTOMATION_VIEW,
                Permission.AUTOMATION_CREATE,
                Permission.AUTOMATION_EXECUTE,
            },
            description='Standard user with basic access'
        )
        self._roles['user'] = user

        # Viewer role: read-only
        viewer = Role(
            name='viewer',
            permissions={
                Permission.INSTRUMENT_VIEW,
                Permission.DATA_VIEW,
                Permission.AUTOMATION_VIEW,
            },
            description='Read-only access'
        )
        self._roles['viewer'] = viewer

        # Operator role: operation permissions
        operator = Role(
            name='operator',
            permissions={
                Permission.INSTRUMENT_VIEW,
                Permission.INSTRUMENT_CONNECT,
                Permission.INSTRUMENT_CONTROL,
                Permission.DATA_VIEW,
                Permission.AUTOMATION_VIEW,
                Permission.AUTOMATION_EXECUTE,
            },
            description='Operator with control access'
        )
        self._roles['operator'] = operator

    def create_role(self, name: str, permissions: Optional[Set[Permission]] = None, description: str = "") -> Role:
        """Create a new role"""
        if name in self._roles:
            raise ValueError(f"Role {name} already exists")

        role = Role(
            name=name,
            permissions=permissions or set(),
            description=description
        )
        self._roles[name] = role
        logger.info(f"Created role: {name}")
        return role

    def delete_role(self, name: str) -> bool:
        """Delete a role"""
        if name in ['admin', 'user', 'viewer', 'operator']:
            raise ValueError(f"Cannot delete system role: {name}")

        if name in self._roles:
            del self._roles[name]
            logger.info(f"Deleted role: {name}")
            return True
        return False

    def get_role(self, name: str) -> Optional[Role]:
        """Get a role by name"""
        return self._roles.get(name)

    def list_roles(self) -> List[Role]:
        """List all roles"""
        return list(self._roles.values())

    def check_permission(self, user_roles: List[str], permission: Permission) -> bool:
        """
        Check if user has a permission

        Args:
            user_roles: List of role names
            permission: Permission to check

        Returns:
            True if user has permission
        """
        for role_name in user_roles:
            role = self._roles.get(role_name)
            if role and role.has_permission(permission):
                return True
        return False

    def get_user_permissions(self, user_roles: List[str]) -> Set[Permission]:
        """Get all permissions for a user"""
        permissions = set()
        for role_name in user_roles:
            role = self._roles.get(role_name)
            if role:
                permissions.update(role.permissions)
        return permissions


# Global authorization manager
authz_manager = AuthorizationManager()


def requires_permission(permission: Permission):
    """
    Decorator to require a permission for a function

    Example:
        @requires_permission(Permission.INSTRUMENT_CONTROL)
        def set_voltage(instrument, voltage):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get user from context (this is a simplified example)
            # In a real application, you'd get the current user from a session/context
            user_roles = kwargs.get('_user_roles', ['user'])

            if not authz_manager.check_permission(user_roles, permission):
                raise PermissionError(
                    f"Permission denied: {permission.value} required"
                )

            return func(*args, **kwargs)
        return wrapper
    return decorator
