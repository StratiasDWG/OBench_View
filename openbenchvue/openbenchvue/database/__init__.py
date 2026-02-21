"""
Database Package

SQLAlchemy-based persistence layer with repository pattern.

Features:
- Connection pooling
- Session management
- Repository pattern for clean data access
- Support for PostgreSQL, MySQL, SQLite
- Migration support via Alembic
"""

from .models import (
    Base,
    UserModel,
    RoleModel,
    UserRoleModel,
    TokenModel,
    APIKeyModel,
    MFASettingModel,
    InstrumentModel,
    MeasurementModel,
    MeasurementBatchModel,
    AuditEventModel,
    SequenceModel,
    ExecutionModel,
    WorkflowModel,
    WorkflowInstanceModel,
    WorkflowTransitionLogModel,
    ConfigurationModel,
    PluginMetadataModel,
    NotificationRuleModel,
    NotificationLogModel,
    BackupModel,
    AnomalyModel,
)

from .connection import (
    DatabaseConfig,
    DatabaseConnection,
    get_database,
    init_database,
    shutdown_database,
    get_session,
    create_sqlite_url,
    create_postgresql_url,
    create_mysql_url,
)

from .repositories import (
    BaseRepository,
    UserRepository,
    InstrumentRepository,
    MeasurementRepository,
    AuditRepository,
)

__all__ = [
    # Models
    'Base',
    'UserModel',
    'RoleModel',
    'UserRoleModel',
    'TokenModel',
    'APIKeyModel',
    'MFASettingModel',
    'InstrumentModel',
    'MeasurementModel',
    'MeasurementBatchModel',
    'AuditEventModel',
    'SequenceModel',
    'ExecutionModel',
    'WorkflowModel',
    'WorkflowInstanceModel',
    'WorkflowTransitionLogModel',
    'ConfigurationModel',
    'PluginMetadataModel',
    'NotificationRuleModel',
    'NotificationLogModel',
    'BackupModel',
    'AnomalyModel',

    # Connection
    'DatabaseConfig',
    'DatabaseConnection',
    'get_database',
    'init_database',
    'shutdown_database',
    'get_session',
    'create_sqlite_url',
    'create_postgresql_url',
    'create_mysql_url',

    # Repositories
    'BaseRepository',
    'UserRepository',
    'InstrumentRepository',
    'MeasurementRepository',
    'AuditRepository',
]
