"""
Security Features for OpenBenchVue

Authentication, authorization, encryption, and audit logging.
"""

from .authentication import (
    AuthenticationManager,
    User,
    Token,
    hash_password,
    verify_password,
)
from .authorization import (
    AuthorizationManager,
    Permission,
    Role,
    requires_permission,
    authz_manager,
)
from .encryption import (
    EncryptionManager,
    encrypt_data,
    decrypt_data,
    get_encryption_manager,
)
from .audit import (
    AuditLogger,
    AuditEvent,
    AuditLevel,
    audit_logger,
)

__all__ = [
    'AuthenticationManager',
    'User',
    'Token',
    'hash_password',
    'verify_password',
    'AuthorizationManager',
    'Permission',
    'Role',
    'requires_permission',
    'authz_manager',
    'EncryptionManager',
    'encrypt_data',
    'decrypt_data',
    'get_encryption_manager',
    'AuditLogger',
    'AuditEvent',
    'AuditLevel',
    'audit_logger',
]
