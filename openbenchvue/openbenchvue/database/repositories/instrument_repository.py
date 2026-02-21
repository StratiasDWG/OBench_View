"""
Instrument Repository

Data access layer for instrument management.
"""

import logging
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from ..models import InstrumentModel
from .base import BaseRepository

logger = logging.getLogger(__name__)


class InstrumentRepository(BaseRepository[InstrumentModel]):
    """Repository for instrument operations"""

    def __init__(self, session: Session):
        super().__init__(InstrumentModel, session)

    def get_by_resource(self, resource_string: str) -> Optional[InstrumentModel]:
        """Get instrument by resource string"""
        return self.session.query(InstrumentModel).filter_by(
            resource_string=resource_string
        ).first()

    def get_by_serial(self, serial_number: str) -> Optional[InstrumentModel]:
        """Get instrument by serial number"""
        return self.session.query(InstrumentModel).filter_by(
            serial_number=serial_number
        ).first()

    def get_by_type(self, instrument_type: str, active_only: bool = True) -> List[InstrumentModel]:
        """Get instruments by type"""
        query = self.session.query(InstrumentModel).filter_by(instrument_type=instrument_type)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.all()

    def get_active_instruments(self) -> List[InstrumentModel]:
        """Get all active instruments"""
        return self.session.query(InstrumentModel).filter_by(is_active=True).all()

    def update_last_seen(self, instrument_id: int) -> bool:
        """Update last seen timestamp"""
        instrument = self.get_by_id(instrument_id)
        if instrument:
            instrument.last_seen = datetime.utcnow()
            self.session.flush()
            return True
        return False

    def mark_inactive(self, instrument_id: int) -> bool:
        """Mark instrument as inactive"""
        instrument = self.get_by_id(instrument_id)
        if instrument:
            instrument.is_active = False
            self.session.flush()
            logger.info(f"Marked instrument {instrument_id} as inactive")
            return True
        return False

    def get_stale_instruments(self, hours: int = 24) -> List[InstrumentModel]:
        """Get instruments not seen in specified hours"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return self.session.query(InstrumentModel).filter(
            InstrumentModel.last_seen < cutoff,
            InstrumentModel.is_active == True
        ).all()

    def update_configuration(self, instrument_id: int, configuration: dict) -> bool:
        """Update instrument configuration"""
        instrument = self.get_by_id(instrument_id)
        if instrument:
            instrument.configuration = configuration
            self.session.flush()
            return True
        return False
