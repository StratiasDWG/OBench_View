"""
Database Connection Management

Handles database connections, connection pooling, and session management.
"""

import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager
from sqlalchemy import create_engine, event, pool
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import Engine
import time

from .models import Base

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration"""

    def __init__(
        self,
        url: str,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        echo: bool = False,
        echo_pool: bool = False,
    ):
        """
        Initialize database configuration

        Args:
            url: Database connection URL
            pool_size: Number of connections to maintain
            max_overflow: Max connections beyond pool_size
            pool_timeout: Timeout for getting connection from pool (seconds)
            pool_recycle: Recycle connections after this time (seconds)
            echo: Echo all SQL statements
            echo_pool: Echo connection pool events
        """
        self.url = url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.echo = echo
        self.echo_pool = echo_pool


class DatabaseConnection:
    """Database connection manager with pooling support"""

    def __init__(self, config: DatabaseConfig):
        """
        Initialize database connection

        Args:
            config: Database configuration
        """
        self.config = config
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._scoped_session: Optional[scoped_session] = None
        self._connection_count = 0

    def connect(self) -> Engine:
        """
        Create database engine and session factory

        Returns:
            SQLAlchemy engine
        """
        if self._engine is not None:
            logger.warning("Database already connected")
            return self._engine

        try:
            logger.info(f"Connecting to database: {self._sanitize_url(self.config.url)}")

            # Create engine with connection pooling
            self._engine = create_engine(
                self.config.url,
                poolclass=pool.QueuePool,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle,
                pool_pre_ping=True,  # Verify connections before using
                echo=self.config.echo,
                echo_pool=self.config.echo_pool,
            )

            # Create session factory
            self._session_factory = sessionmaker(
                bind=self._engine,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )

            # Create scoped session for thread-local sessions
            self._scoped_session = scoped_session(self._session_factory)

            # Register event listeners
            self._register_event_listeners()

            # Test connection
            with self._engine.connect() as conn:
                logger.info("Database connection successful")

            return self._engine

        except SQLAlchemyError as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def disconnect(self):
        """Close database connection and cleanup resources"""
        if self._engine is None:
            return

        try:
            logger.info("Disconnecting from database...")

            # Close scoped session
            if self._scoped_session:
                self._scoped_session.remove()

            # Dispose engine and close all connections
            self._engine.dispose()

            self._engine = None
            self._session_factory = None
            self._scoped_session = None

            logger.info("Database disconnected")

        except Exception as e:
            logger.error(f"Error during database disconnect: {e}")

    def create_tables(self):
        """Create all tables defined in models"""
        if self._engine is None:
            raise RuntimeError("Database not connected")

        try:
            logger.info("Creating database tables...")
            Base.metadata.create_all(self._engine)
            logger.info("Database tables created successfully")

        except SQLAlchemyError as e:
            logger.error(f"Failed to create tables: {e}")
            raise

    def drop_tables(self):
        """Drop all tables (WARNING: destructive operation)"""
        if self._engine is None:
            raise RuntimeError("Database not connected")

        try:
            logger.warning("Dropping all database tables...")
            Base.metadata.drop_all(self._engine)
            logger.info("Database tables dropped")

        except SQLAlchemyError as e:
            logger.error(f"Failed to drop tables: {e}")
            raise

    def get_session(self) -> Session:
        """
        Get a new database session

        Returns:
            SQLAlchemy Session
        """
        if self._session_factory is None:
            raise RuntimeError("Database not connected")

        return self._session_factory()

    def get_scoped_session(self) -> scoped_session:
        """
        Get thread-local scoped session

        Returns:
            Scoped session
        """
        if self._scoped_session is None:
            raise RuntimeError("Database not connected")

        return self._scoped_session

    @contextmanager
    def session_scope(self):
        """
        Provide a transactional scope around a series of operations

        Usage:
            with db.session_scope() as session:
                user = session.query(UserModel).filter_by(username='admin').first()
                user.email = 'new@example.com'
                # Automatic commit on success, rollback on exception
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Session error, rolling back: {e}")
            raise
        finally:
            session.close()

    def execute_raw(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute raw SQL query

        Args:
            sql: SQL statement
            params: Query parameters

        Returns:
            Query result
        """
        if self._engine is None:
            raise RuntimeError("Database not connected")

        with self._engine.connect() as conn:
            result = conn.execute(sql, params or {})
            return result

    def get_pool_status(self) -> Dict[str, Any]:
        """
        Get connection pool status

        Returns:
            Dictionary with pool statistics
        """
        if self._engine is None or self._engine.pool is None:
            return {}

        pool = self._engine.pool
        return {
            'size': pool.size(),
            'checked_in': pool.checkedin(),
            'checked_out': pool.checkedout(),
            'overflow': pool.overflow(),
            'total_connections': pool.size() + pool.overflow(),
        }

    def _register_event_listeners(self):
        """Register SQLAlchemy event listeners for monitoring"""
        if self._engine is None:
            return

        # Log slow queries
        @event.listens_for(self._engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            conn.info.setdefault('query_start_time', []).append(time.time())

        @event.listens_for(self._engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total_time = time.time() - conn.info['query_start_time'].pop()
            if total_time > 1.0:  # Log queries taking > 1 second
                logger.warning(f"Slow query ({total_time:.2f}s): {statement[:200]}")

        # Track connection events
        @event.listens_for(self._engine, "connect")
        def connect(dbapi_conn, connection_record):
            self._connection_count += 1
            logger.debug(f"Connection established (total: {self._connection_count})")

        @event.listens_for(self._engine, "close")
        def close(dbapi_conn, connection_record):
            logger.debug("Connection closed")

    @staticmethod
    def _sanitize_url(url: str) -> str:
        """Remove password from URL for logging"""
        try:
            from sqlalchemy.engine.url import make_url
            parsed = make_url(url)
            if parsed.password:
                parsed = parsed.set(password='***')
            return str(parsed)
        except Exception:
            return url


# ============================================================================
# Global Database Instance
# ============================================================================

_db_connection: Optional[DatabaseConnection] = None


def get_database() -> DatabaseConnection:
    """
    Get global database connection instance

    Returns:
        DatabaseConnection instance
    """
    global _db_connection
    if _db_connection is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _db_connection


def init_database(config: DatabaseConfig) -> DatabaseConnection:
    """
    Initialize global database connection

    Args:
        config: Database configuration

    Returns:
        DatabaseConnection instance
    """
    global _db_connection

    if _db_connection is not None:
        logger.warning("Database already initialized")
        return _db_connection

    _db_connection = DatabaseConnection(config)
    _db_connection.connect()

    return _db_connection


def shutdown_database():
    """Shutdown global database connection"""
    global _db_connection

    if _db_connection is not None:
        _db_connection.disconnect()
        _db_connection = None


@contextmanager
def get_session():
    """
    Get database session as context manager

    Usage:
        with get_session() as session:
            users = session.query(UserModel).all()
    """
    db = get_database()
    with db.session_scope() as session:
        yield session


# ============================================================================
# Database Utilities
# ============================================================================

def create_sqlite_url(path: str = 'openbenchvue.db') -> str:
    """Create SQLite database URL"""
    return f'sqlite:///{path}'


def create_postgresql_url(
    host: str = 'localhost',
    port: int = 5432,
    database: str = 'openbenchvue',
    username: str = 'openbenchvue',
    password: str = 'password',
) -> str:
    """Create PostgreSQL database URL"""
    return f'postgresql://{username}:{password}@{host}:{port}/{database}'


def create_mysql_url(
    host: str = 'localhost',
    port: int = 3306,
    database: str = 'openbenchvue',
    username: str = 'openbenchvue',
    password: str = 'password',
) -> str:
    """Create MySQL database URL"""
    return f'mysql+pymysql://{username}:{password}@{host}:{port}/{database}'
