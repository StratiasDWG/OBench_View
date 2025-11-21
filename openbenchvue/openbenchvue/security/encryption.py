"""
Encryption Utilities

Data encryption for sensitive information.
"""

import base64
import hashlib
import secrets
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class EncryptionManager:
    """
    Manages data encryption using AES

    Note: For production use, consider using libraries like cryptography
    """

    def __init__(self, key: Optional[bytes] = None):
        """
        Initialize encryption manager

        Args:
            key: Encryption key (32 bytes for AES-256)
        """
        if key is None:
            # Generate random key
            self.key = secrets.token_bytes(32)
            logger.warning("Generated random encryption key. Save it securely!")
        else:
            self.key = key

        try:
            from cryptography.fernet import Fernet
            # Derive Fernet key from our key
            fernet_key = base64.urlsafe_b64encode(hashlib.sha256(self.key).digest())
            self._fernet = Fernet(fernet_key)
            self._available = True
        except ImportError:
            logger.warning("cryptography library not available. Using basic encoding.")
            self._fernet = None
            self._available = False

    def encrypt(self, data: bytes) -> bytes:
        """
        Encrypt data

        Args:
            data: Data to encrypt

        Returns:
            Encrypted data
        """
        if self._fernet:
            return self._fernet.encrypt(data)
        else:
            # Fallback: just base64 encode (NOT SECURE!)
            logger.warning("Using insecure fallback encryption!")
            return base64.b64encode(data)

    def decrypt(self, encrypted_data: bytes) -> bytes:
        """
        Decrypt data

        Args:
            encrypted_data: Encrypted data

        Returns:
            Decrypted data
        """
        if self._fernet:
            return self._fernet.decrypt(encrypted_data)
        else:
            # Fallback: base64 decode
            return base64.b64decode(encrypted_data)

    def encrypt_string(self, text: str) -> str:
        """
        Encrypt a string

        Args:
            text: Plain text string

        Returns:
            Base64-encoded encrypted string
        """
        encrypted = self.encrypt(text.encode('utf-8'))
        return base64.b64encode(encrypted).decode('ascii')

    def decrypt_string(self, encrypted_text: str) -> str:
        """
        Decrypt a string

        Args:
            encrypted_text: Base64-encoded encrypted string

        Returns:
            Decrypted plain text
        """
        encrypted = base64.b64decode(encrypted_text.encode('ascii'))
        decrypted = self.decrypt(encrypted)
        return decrypted.decode('utf-8')


# Global encryption manager
_encryption_manager = None


def get_encryption_manager() -> EncryptionManager:
    """Get global encryption manager"""
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    return _encryption_manager


def encrypt_data(data: bytes) -> bytes:
    """Convenience function to encrypt data"""
    return get_encryption_manager().encrypt(data)


def decrypt_data(encrypted_data: bytes) -> bytes:
    """Convenience function to decrypt data"""
    return get_encryption_manager().decrypt(encrypted_data)
