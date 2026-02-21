"""
Base Repository Pattern

Provides generic CRUD operations for database models.
"""

import logging
from typing import TypeVar, Generic, Type, Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

T = TypeVar('T')  # Generic type for model


class BaseRepository(Generic[T]):
    """Base repository with generic CRUD operations"""

    def __init__(self, model_class: Type[T], session: Session):
        """
        Initialize repository

        Args:
            model_class: SQLAlchemy model class
            session: Database session
        """
        self.model_class = model_class
        self.session = session

    def create(self, **kwargs) -> T:
        """
        Create a new record

        Args:
            **kwargs: Model attributes

        Returns:
            Created model instance
        """
        try:
            instance = self.model_class(**kwargs)
            self.session.add(instance)
            self.session.flush()  # Flush to get ID without committing
            logger.debug(f"Created {self.model_class.__name__}: {instance.id if hasattr(instance, 'id') else ''}")
            return instance

        except SQLAlchemyError as e:
            logger.error(f"Error creating {self.model_class.__name__}: {e}")
            raise

    def get_by_id(self, id: int) -> Optional[T]:
        """
        Get record by ID

        Args:
            id: Record ID

        Returns:
            Model instance or None
        """
        try:
            return self.session.query(self.model_class).filter_by(id=id).first()

        except SQLAlchemyError as e:
            logger.error(f"Error getting {self.model_class.__name__} by ID {id}: {e}")
            raise

    def get_by_field(self, **kwargs) -> Optional[T]:
        """
        Get single record by field values

        Args:
            **kwargs: Field names and values

        Returns:
            Model instance or None
        """
        try:
            return self.session.query(self.model_class).filter_by(**kwargs).first()

        except SQLAlchemyError as e:
            logger.error(f"Error getting {self.model_class.__name__} by fields {kwargs}: {e}")
            raise

    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[T]:
        """
        Get all records

        Args:
            limit: Maximum number of records
            offset: Number of records to skip

        Returns:
            List of model instances
        """
        try:
            query = self.session.query(self.model_class)
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            return query.all()

        except SQLAlchemyError as e:
            logger.error(f"Error getting all {self.model_class.__name__}: {e}")
            raise

    def filter(self, **kwargs) -> List[T]:
        """
        Filter records by field values

        Args:
            **kwargs: Field names and values

        Returns:
            List of matching model instances
        """
        try:
            return self.session.query(self.model_class).filter_by(**kwargs).all()

        except SQLAlchemyError as e:
            logger.error(f"Error filtering {self.model_class.__name__}: {e}")
            raise

    def update(self, id: int, **kwargs) -> Optional[T]:
        """
        Update record by ID

        Args:
            id: Record ID
            **kwargs: Fields to update

        Returns:
            Updated model instance or None
        """
        try:
            instance = self.get_by_id(id)
            if instance is None:
                logger.warning(f"{self.model_class.__name__} with ID {id} not found")
                return None

            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)

            self.session.flush()
            logger.debug(f"Updated {self.model_class.__name__} ID {id}")
            return instance

        except SQLAlchemyError as e:
            logger.error(f"Error updating {self.model_class.__name__} ID {id}: {e}")
            raise

    def delete(self, id: int) -> bool:
        """
        Delete record by ID

        Args:
            id: Record ID

        Returns:
            True if deleted, False if not found
        """
        try:
            instance = self.get_by_id(id)
            if instance is None:
                logger.warning(f"{self.model_class.__name__} with ID {id} not found")
                return False

            self.session.delete(instance)
            self.session.flush()
            logger.debug(f"Deleted {self.model_class.__name__} ID {id}")
            return True

        except SQLAlchemyError as e:
            logger.error(f"Error deleting {self.model_class.__name__} ID {id}: {e}")
            raise

    def count(self, **kwargs) -> int:
        """
        Count records

        Args:
            **kwargs: Optional filter criteria

        Returns:
            Number of records
        """
        try:
            query = self.session.query(self.model_class)
            if kwargs:
                query = query.filter_by(**kwargs)
            return query.count()

        except SQLAlchemyError as e:
            logger.error(f"Error counting {self.model_class.__name__}: {e}")
            raise

    def exists(self, **kwargs) -> bool:
        """
        Check if record exists

        Args:
            **kwargs: Field names and values

        Returns:
            True if exists, False otherwise
        """
        try:
            return self.session.query(
                self.session.query(self.model_class).filter_by(**kwargs).exists()
            ).scalar()

        except SQLAlchemyError as e:
            logger.error(f"Error checking existence of {self.model_class.__name__}: {e}")
            raise

    def bulk_create(self, records: List[Dict[str, Any]]) -> List[T]:
        """
        Create multiple records in bulk

        Args:
            records: List of dictionaries with model attributes

        Returns:
            List of created instances
        """
        try:
            instances = [self.model_class(**record) for record in records]
            self.session.bulk_save_objects(instances, return_defaults=True)
            self.session.flush()
            logger.debug(f"Bulk created {len(instances)} {self.model_class.__name__} records")
            return instances

        except SQLAlchemyError as e:
            logger.error(f"Error bulk creating {self.model_class.__name__}: {e}")
            raise

    def bulk_update(self, updates: List[Dict[str, Any]], id_field: str = 'id') -> int:
        """
        Update multiple records in bulk

        Args:
            updates: List of dictionaries with ID and fields to update
            id_field: Name of ID field (default: 'id')

        Returns:
            Number of records updated
        """
        try:
            count = self.session.bulk_update_mappings(self.model_class, updates)
            self.session.flush()
            logger.debug(f"Bulk updated {count} {self.model_class.__name__} records")
            return count

        except SQLAlchemyError as e:
            logger.error(f"Error bulk updating {self.model_class.__name__}: {e}")
            raise
