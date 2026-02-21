"""
Audit Repository

Data access layer for audit log events.
"""

import logging
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models import AuditEventModel
from .base import BaseRepository

logger = logging.getLogger(__name__)


class AuditRepository(BaseRepository[AuditEventModel]):
    """Repository for audit log operations"""

    def __init__(self, session: Session):
        super().__init__(AuditEventModel, session)

    def log_event(
        self,
        event_type: str,
        action: str,
        username: Optional[str],
        result: str,
        reason: Optional[str] = None,
        resource: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> AuditEventModel:
        """Create audit log event"""
        event = self.create(
            event_type=event_type,
            action=action,
            username=username,
            result=result,
            reason=reason,
            resource=resource,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata
        )
        logger.debug(f"Audit log: {event_type}/{action} by {username}: {result}")
        return event

    def get_user_events(
        self,
        username: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[AuditEventModel]:
        """Get audit events for a user"""
        query = self.session.query(AuditEventModel).filter_by(username=username)

        if start_time:
            query = query.filter(AuditEventModel.timestamp >= start_time)
        if end_time:
            query = query.filter(AuditEventModel.timestamp <= end_time)
        if event_type:
            query = query.filter_by(event_type=event_type)

        return query.order_by(AuditEventModel.timestamp.desc()).limit(limit).all()

    def get_failed_login_attempts(
        self,
        username: Optional[str] = None,
        hours: int = 24
    ) -> List[AuditEventModel]:
        """Get failed login attempts"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        query = self.session.query(AuditEventModel).filter(
            AuditEventModel.event_type == 'authentication',
            AuditEventModel.action == 'login',
            AuditEventModel.result == 'failure',
            AuditEventModel.timestamp >= cutoff
        )

        if username:
            query = query.filter_by(username=username)

        return query.order_by(AuditEventModel.timestamp.desc()).all()

    def get_events_by_type(
        self,
        event_type: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditEventModel]:
        """Get events by type"""
        query = self.session.query(AuditEventModel).filter_by(event_type=event_type)

        if start_time:
            query = query.filter(AuditEventModel.timestamp >= start_time)
        if end_time:
            query = query.filter(AuditEventModel.timestamp <= end_time)

        return query.order_by(AuditEventModel.timestamp.desc()).limit(limit).all()

    def get_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> dict:
        """Get audit log statistics"""
        query = self.session.query(AuditEventModel)

        if start_time:
            query = query.filter(AuditEventModel.timestamp >= start_time)
        if end_time:
            query = query.filter(AuditEventModel.timestamp <= end_time)

        # Total events
        total = query.count()

        # Events by type
        by_type = dict(
            query.with_entities(
                AuditEventModel.event_type,
                func.count(AuditEventModel.id)
            ).group_by(AuditEventModel.event_type).all()
        )

        # Events by result
        by_result = dict(
            query.with_entities(
                AuditEventModel.result,
                func.count(AuditEventModel.id)
            ).group_by(AuditEventModel.result).all()
        )

        # Top users
        top_users = query.with_entities(
            AuditEventModel.username,
            func.count(AuditEventModel.id).label('count')
        ).filter(
            AuditEventModel.username.isnot(None)
        ).group_by(
            AuditEventModel.username
        ).order_by(
            func.count(AuditEventModel.id).desc()
        ).limit(10).all()

        return {
            'total_events': total,
            'by_type': by_type,
            'by_result': by_result,
            'top_users': [(username, count) for username, count in top_users]
        }

    def cleanup_old_events(self, days: int = 90) -> int:
        """Delete audit events older than specified days"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        count = self.session.query(AuditEventModel).filter(
            AuditEventModel.timestamp < cutoff
        ).delete()
        self.session.flush()
        logger.info(f"Cleaned up {count} audit events older than {days} days")
        return count
