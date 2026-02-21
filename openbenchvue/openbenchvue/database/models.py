"""
Database Models for OpenBenchVue

SQLAlchemy ORM models for persistent storage.
"""

import enum
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, JSON,
    ForeignKey, Enum, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


# ============================================================================
# User & Authentication Models
# ============================================================================

class UserModel(Base):
    """User account model"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=True, index=True)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_locked = Column(Boolean, default=False, nullable=False)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    roles = relationship('UserRoleModel', back_populates='user', cascade='all, delete-orphan')
    tokens = relationship('TokenModel', back_populates='user', cascade='all, delete-orphan')
    api_keys = relationship('APIKeyModel', back_populates='user', cascade='all, delete-orphan')
    mfa_settings = relationship('MFASettingModel', back_populates='user', uselist=False, cascade='all, delete-orphan')

    __table_args__ = (
        CheckConstraint('failed_login_attempts >= 0', name='check_failed_attempts'),
        Index('idx_user_active', 'is_active'),
    )


class RoleModel(Base):
    """Role model for RBAC"""
    __tablename__ = 'roles'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    permissions = Column(JSON, nullable=False)  # List of permission strings
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    users = relationship('UserRoleModel', back_populates='role')


class UserRoleModel(Base):
    """User-Role association (many-to-many)"""
    __tablename__ = 'user_roles'

    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    role_id = Column(Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True)
    assigned_at = Column(DateTime, default=func.now(), nullable=False)
    assigned_by = Column(String(50), nullable=True)

    # Relationships
    user = relationship('UserModel', back_populates='roles')
    role = relationship('RoleModel', back_populates='users')


class TokenModel(Base):
    """Authentication token model"""
    __tablename__ = 'tokens'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    refresh_token = Column(String(255), unique=True, nullable=True, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    ip_address = Column(String(45), nullable=True)  # Support IPv6
    user_agent = Column(String(500), nullable=True)

    # Relationships
    user = relationship('UserModel', back_populates='tokens')

    __table_args__ = (
        Index('idx_token_expiry', 'expires_at'),
    )


class APIKeyModel(Base):
    """API key model for programmatic access"""
    __tablename__ = 'api_keys'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    prefix = Column(String(10), nullable=False)  # First few chars for identification
    scopes = Column(JSON, nullable=False)  # List of allowed operations
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime, nullable=True, index=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    user = relationship('UserModel', back_populates='api_keys')


class MFASettingModel(Base):
    """Multi-factor authentication settings"""
    __tablename__ = 'mfa_settings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False, index=True)
    enabled = Column(Boolean, default=False, nullable=False)
    method = Column(String(20), nullable=True)  # 'totp', 'sms', 'email'
    secret = Column(String(255), nullable=True)  # Encrypted TOTP secret
    backup_codes = Column(JSON, nullable=True)  # Hashed backup codes
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship('UserModel', back_populates='mfa_settings')


# ============================================================================
# Instrument Models
# ============================================================================

class InstrumentModel(Base):
    """Instrument metadata model"""
    __tablename__ = 'instruments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_string = Column(String(255), unique=True, nullable=False, index=True)
    instrument_type = Column(String(50), nullable=False, index=True)
    manufacturer = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    serial_number = Column(String(100), nullable=True, index=True)
    firmware_version = Column(String(50), nullable=True)
    capabilities = Column(JSON, nullable=True)
    configuration = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_seen = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    measurements = relationship('MeasurementModel', back_populates='instrument', cascade='all, delete-orphan')

    __table_args__ = (
        Index('idx_instrument_type_active', 'instrument_type', 'is_active'),
    )


# ============================================================================
# Measurement Models (Time-Series Optimized)
# ============================================================================

class MeasurementModel(Base):
    """Measurement data model (time-series)"""
    __tablename__ = 'measurements'

    id = Column(Integer, primary_key=True, autoincrement=True)
    instrument_id = Column(Integer, ForeignKey('instruments.id', ondelete='CASCADE'), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    measurement_type = Column(String(50), nullable=False, index=True)  # 'voltage', 'current', etc.
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    range_setting = Column(String(50), nullable=True)
    quality = Column(Float, nullable=True)  # Quality indicator 0-1
    metadata = Column(JSON, nullable=True)  # Additional context

    # Relationships
    instrument = relationship('InstrumentModel', back_populates='measurements')

    __table_args__ = (
        Index('idx_measurement_time', 'timestamp'),
        Index('idx_measurement_instrument_time', 'instrument_id', 'timestamp'),
        Index('idx_measurement_type_time', 'measurement_type', 'timestamp'),
    )


class MeasurementBatchModel(Base):
    """Batch measurement storage for high-frequency data"""
    __tablename__ = 'measurement_batches'

    id = Column(Integer, primary_key=True, autoincrement=True)
    instrument_id = Column(Integer, ForeignKey('instruments.id', ondelete='CASCADE'), nullable=False, index=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    measurement_type = Column(String(50), nullable=False)
    sample_rate = Column(Float, nullable=False)  # Samples per second
    count = Column(Integer, nullable=False)
    values_compressed = Column(Text, nullable=False)  # Base64 encoded compressed array
    unit = Column(String(20), nullable=False)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_batch_instrument_time', 'instrument_id', 'start_time', 'end_time'),
    )


# ============================================================================
# Audit & Security Models
# ============================================================================

class AuditEventModel(Base):
    """Audit log event model"""
    __tablename__ = 'audit_events'

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=func.now(), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)  # 'authentication', 'authorization', etc.
    action = Column(String(100), nullable=False)
    username = Column(String(50), nullable=True, index=True)
    result = Column(String(20), nullable=False)  # 'success', 'failure'
    reason = Column(String(255), nullable=True)
    resource = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index('idx_audit_type_time', 'event_type', 'timestamp'),
        Index('idx_audit_user_time', 'username', 'timestamp'),
        Index('idx_audit_result', 'result'),
    )


# ============================================================================
# Automation & Workflow Models
# ============================================================================

class SequenceModel(Base):
    """Test sequence model"""
    __tablename__ = 'sequences'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    version = Column(String(20), nullable=False)
    author = Column(String(100), nullable=True)
    blocks = Column(JSON, nullable=False)  # Sequence definition
    variables = Column(JSON, nullable=True)  # Default variables
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    executions = relationship('ExecutionModel', back_populates='sequence', cascade='all, delete-orphan')

    __table_args__ = (
        UniqueConstraint('name', 'version', name='uq_sequence_name_version'),
    )


class ExecutionModel(Base):
    """Sequence execution record"""
    __tablename__ = 'executions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    sequence_id = Column(Integer, ForeignKey('sequences.id', ondelete='CASCADE'), nullable=False, index=True)
    started_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    state = Column(String(20), nullable=False, index=True)  # 'running', 'completed', 'failed'
    blocks_executed = Column(Integer, default=0, nullable=False)
    blocks_total = Column(Integer, nullable=False)
    variables = Column(JSON, nullable=True)
    results = Column(JSON, nullable=True)
    errors = Column(JSON, nullable=True)
    executed_by = Column(String(50), nullable=True)

    # Relationships
    sequence = relationship('SequenceModel', back_populates='executions')

    __table_args__ = (
        Index('idx_execution_state_time', 'state', 'started_at'),
    )


class WorkflowModel(Base):
    """Workflow definition model"""
    __tablename__ = 'workflows'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    version = Column(String(20), nullable=False)
    states = Column(JSON, nullable=False)  # State definitions
    transitions = Column(JSON, nullable=False)  # Transition rules
    initial_state = Column(String(50), nullable=False)
    final_states = Column(JSON, nullable=False)  # List of terminal states
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    instances = relationship('WorkflowInstanceModel', back_populates='workflow', cascade='all, delete-orphan')


class WorkflowInstanceModel(Base):
    """Workflow instance (execution) model"""
    __tablename__ = 'workflow_instances'

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(Integer, ForeignKey('workflows.id', ondelete='CASCADE'), nullable=False, index=True)
    current_state = Column(String(50), nullable=False, index=True)
    context = Column(JSON, nullable=True)  # Workflow context/variables
    started_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, index=True)  # 'active', 'completed', 'failed'

    # Relationships
    workflow = relationship('WorkflowModel', back_populates='instances')
    transitions = relationship('WorkflowTransitionLogModel', back_populates='instance', cascade='all, delete-orphan')


class WorkflowTransitionLogModel(Base):
    """Workflow transition log"""
    __tablename__ = 'workflow_transitions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey('workflow_instances.id', ondelete='CASCADE'), nullable=False, index=True)
    from_state = Column(String(50), nullable=False)
    to_state = Column(String(50), nullable=False)
    event = Column(String(100), nullable=True)
    timestamp = Column(DateTime, default=func.now(), nullable=False, index=True)
    metadata = Column(JSON, nullable=True)

    # Relationships
    instance = relationship('WorkflowInstanceModel', back_populates='transitions')


# ============================================================================
# Configuration & Settings Models
# ============================================================================

class ConfigurationModel(Base):
    """System configuration model"""
    __tablename__ = 'configurations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)
    is_encrypted = Column(Boolean, default=False, nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    updated_by = Column(String(50), nullable=True)


class PluginMetadataModel(Base):
    """Plugin metadata and state"""
    __tablename__ = 'plugins'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    version = Column(String(20), nullable=False)
    plugin_type = Column(String(50), nullable=False, index=True)
    author = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    is_enabled = Column(Boolean, default=False, nullable=False)
    is_loaded = Column(Boolean, default=False, nullable=False)
    configuration = Column(JSON, nullable=True)
    dependencies = Column(JSON, nullable=True)
    installed_at = Column(DateTime, default=func.now(), nullable=False)
    last_loaded_at = Column(DateTime, nullable=True)


# ============================================================================
# Notification Models
# ============================================================================

class NotificationRuleModel(Base):
    """Notification rule model"""
    __tablename__ = 'notification_rules'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    trigger_type = Column(String(50), nullable=False, index=True)  # 'anomaly', 'threshold', 'event'
    conditions = Column(JSON, nullable=False)
    channels = Column(JSON, nullable=False)  # ['email', 'slack', 'sms']
    recipients = Column(JSON, nullable=False)
    priority = Column(String(20), default='medium', nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


class NotificationLogModel(Base):
    """Notification delivery log"""
    __tablename__ = 'notification_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(Integer, ForeignKey('notification_rules.id', ondelete='SET NULL'), nullable=True, index=True)
    channel = Column(String(50), nullable=False)
    recipient = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=True)
    message = Column(Text, nullable=False)
    priority = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, index=True)  # 'sent', 'failed', 'pending'
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)


# ============================================================================
# Backup Models
# ============================================================================

class BackupModel(Base):
    """Backup metadata model"""
    __tablename__ = 'backups'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    backup_type = Column(String(20), nullable=False)  # 'full', 'incremental', 'differential'
    storage_type = Column(String(50), nullable=False)  # 'local', 's3', 'azure'
    storage_path = Column(String(1000), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    compressed = Column(Boolean, default=True, nullable=False)
    encrypted = Column(Boolean, default=True, nullable=False)
    checksum = Column(String(64), nullable=False)  # SHA256
    status = Column(String(20), nullable=False, index=True)  # 'completed', 'failed', 'in_progress'
    started_at = Column(DateTime, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True)


# ============================================================================
# Analytics Models
# ============================================================================

class AnomalyModel(Base):
    """Detected anomaly model"""
    __tablename__ = 'anomalies'

    id = Column(Integer, primary_key=True, autoincrement=True)
    instrument_id = Column(Integer, ForeignKey('instruments.id', ondelete='CASCADE'), nullable=False, index=True)
    detected_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    anomaly_type = Column(String(50), nullable=False, index=True)  # 'spike', 'drop', 'drift', etc.
    severity = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    measurement_value = Column(Float, nullable=False)
    expected_value = Column(Float, nullable=True)
    threshold = Column(Float, nullable=True)
    metadata = Column(JSON, nullable=True)
    acknowledged = Column(Boolean, default=False, nullable=False)
    acknowledged_by = Column(String(50), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index('idx_anomaly_instrument_time', 'instrument_id', 'detected_at'),
        Index('idx_anomaly_type_severity', 'anomaly_type', 'severity'),
    )
