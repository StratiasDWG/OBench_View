"""
Measurement Repository

Data access layer for measurement data (time-series optimized).
"""

import logging
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from ..models import MeasurementModel, MeasurementBatchModel
from .base import BaseRepository

logger = logging.getLogger(__name__)


class MeasurementRepository(BaseRepository[MeasurementModel]):
    """Repository for measurement operations"""

    def __init__(self, session: Session):
        super().__init__(MeasurementModel, session)

    def get_instrument_measurements(
        self,
        instrument_id: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        measurement_type: Optional[str] = None,
        limit: Optional[int] = 1000
    ) -> List[MeasurementModel]:
        """Get measurements for an instrument with optional filters"""
        query = self.session.query(MeasurementModel).filter_by(instrument_id=instrument_id)

        if start_time:
            query = query.filter(MeasurementModel.timestamp >= start_time)
        if end_time:
            query = query.filter(MeasurementModel.timestamp <= end_time)
        if measurement_type:
            query = query.filter_by(measurement_type=measurement_type)

        query = query.order_by(MeasurementModel.timestamp.desc())

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_latest_measurement(
        self,
        instrument_id: int,
        measurement_type: Optional[str] = None
    ) -> Optional[MeasurementModel]:
        """Get most recent measurement"""
        query = self.session.query(MeasurementModel).filter_by(instrument_id=instrument_id)

        if measurement_type:
            query = query.filter_by(measurement_type=measurement_type)

        return query.order_by(MeasurementModel.timestamp.desc()).first()

    def get_measurement_stats(
        self,
        instrument_id: int,
        measurement_type: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> dict:
        """Get statistical summary of measurements"""
        query = self.session.query(
            func.count(MeasurementModel.id).label('count'),
            func.avg(MeasurementModel.value).label('mean'),
            func.min(MeasurementModel.value).label('min'),
            func.max(MeasurementModel.value).label('max'),
            func.stddev(MeasurementModel.value).label('stddev')
        ).filter_by(
            instrument_id=instrument_id,
            measurement_type=measurement_type
        )

        if start_time:
            query = query.filter(MeasurementModel.timestamp >= start_time)
        if end_time:
            query = query.filter(MeasurementModel.timestamp <= end_time)

        result = query.first()

        return {
            'count': result.count or 0,
            'mean': float(result.mean) if result.mean else 0.0,
            'min': float(result.min) if result.min else 0.0,
            'max': float(result.max) if result.max else 0.0,
            'stddev': float(result.stddev) if result.stddev else 0.0,
        }

    def cleanup_old_measurements(self, days: int = 30) -> int:
        """Delete measurements older than specified days"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        count = self.session.query(MeasurementModel).filter(
            MeasurementModel.timestamp < cutoff
        ).delete()
        self.session.flush()
        logger.info(f"Cleaned up {count} measurements older than {days} days")
        return count

    def get_measurement_rate(
        self,
        instrument_id: int,
        measurement_type: str,
        minutes: int = 5
    ) -> float:
        """Calculate measurement rate (measurements per second)"""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        count = self.session.query(MeasurementModel).filter(
            MeasurementModel.instrument_id == instrument_id,
            MeasurementModel.measurement_type == measurement_type,
            MeasurementModel.timestamp >= cutoff
        ).count()

        return count / (minutes * 60)


class MeasurementBatchRepository(BaseRepository[MeasurementBatchModel]):
    """Repository for batch measurements"""

    def __init__(self, session: Session):
        super().__init__(MeasurementBatchModel, session)

    def get_batches(
        self,
        instrument_id: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        measurement_type: Optional[str] = None
    ) -> List[MeasurementBatchModel]:
        """Get measurement batches with filters"""
        query = self.session.query(MeasurementBatchModel).filter_by(instrument_id=instrument_id)

        if start_time:
            query = query.filter(MeasurementBatchModel.end_time >= start_time)
        if end_time:
            query = query.filter(MeasurementBatchModel.start_time <= end_time)
        if measurement_type:
            query = query.filter_by(measurement_type=measurement_type)

        return query.order_by(MeasurementBatchModel.start_time.desc()).all()
