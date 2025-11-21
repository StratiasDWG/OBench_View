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
)
from .encryption import (
    EncryptionManager,
    encrypt_data,
    decrypt_data,
)
from .audit import (
    AuditLogger,
    AuditEvent,
    AuditLevel,
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
    'EncryptionManager',
    'encrypt_data',
    'decrypt_data',
    'AuditLogger',
    'AuditEvent',
    'AuditLevel',
]
