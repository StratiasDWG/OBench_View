"""
Audit Logging

Comprehensive audit trail for security-relevant events.
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AuditLevel(Enum):
    """Audit event severity levels"""
    INFO = 'info'
    WARNING = 'warning'
    CRITICAL = 'critical'


@dataclass
class AuditEvent:
    """Represents an audit event"""
    timestamp: datetime
    event_type: str
    username: Optional[str]
    action: str
    resource: Optional[str] = None
    result: str = 'success'  # 'success', 'failure', 'error'
    level: AuditLevel = AuditLevel.INFO
    ip_address: Optional[str] = None
    details: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['level'] = self.level.value
        return data

    def to_json(self) -> str:
        """Convert to JSON"""
        return json.dumps(self.to_dict())


class AuditLogger:
    """
    Audit logging system

    Logs security-relevant events for compliance and forensics.
    """

    def __init__(self, log_file: Optional[str] = None, max_events: int = 10000):
        """
        Initialize audit logger

        Args:
            log_file: Path to audit log file
            max_events: Maximum events to keep in memory
        """
        self.log_file = log_file
        self.max_events = max_events
        self._events: List[AuditEvent] = []

        # Configure file logging if specified
        if log_file:
            self._setup_file_logging(log_file)

    def _setup_file_logging(self, log_file: str):
        """Setup file logging for audit events"""
        audit_logger = logging.getLogger('openbenchvue.audit')
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        audit_logger.addHandler(handler)
        audit_logger.setLevel(logging.INFO)

    def log_event(
        self,
        event_type: str,
        action: str,
        username: Optional[str] = None,
        resource: Optional[str] = None,
        result: str = 'success',
        level: AuditLevel = AuditLevel.INFO,
        ip_address: Optional[str] = None,
        **details
    ):
        """
        Log an audit event

        Args:
            event_type: Type of event (e.g., 'authentication', 'authorization')
            action: Action performed (e.g., 'login', 'access_denied')
            username: Username performing the action
            resource: Resource being accessed
            result: Result of the action
            level: Severity level
            ip_address: IP address of the user
            **details: Additional details to log
        """
        event = AuditEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            username=username,
            action=action,
            resource=resource,
            result=result,
            level=level,
            ip_address=ip_address,
            details=details or {},
        )

        # Add to memory
        self._events.append(event)
        if len(self._events) > self.max_events:
            self._events.pop(0)

        # Log to file
        if self.log_file:
            audit_logger = logging.getLogger('openbenchvue.audit')
            audit_logger.info(event.to_json())

        # Also log to main logger based on level
        log_msg = f"[AUDIT] {event_type}:{action} user={username} resource={resource} result={result}"
        if level == AuditLevel.CRITICAL:
            logger.critical(log_msg)
        elif level == AuditLevel.WARNING:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

    def log_authentication(
        self,
        action: str,
        username: str,
        result: str = 'success',
        ip_address: Optional[str] = None,
        **details
    ):
        """Log authentication event"""
        level = AuditLevel.WARNING if result != 'success' else AuditLevel.INFO
        self.log_event(
            event_type='authentication',
            action=action,
            username=username,
            result=result,
            level=level,
            ip_address=ip_address,
            **details
        )

    def log_authorization(
        self,
        action: str,
        username: str,
        resource: str,
        result: str = 'success',
        **details
    ):
        """Log authorization event"""
        level = AuditLevel.WARNING if result != 'success' else AuditLevel.INFO
        self.log_event(
            event_type='authorization',
            action=action,
            username=username,
            resource=resource,
            result=result,
            level=level,
            **details
        )

    def log_data_access(
        self,
        action: str,
        username: str,
        resource: str,
        **details
    ):
        """Log data access event"""
        self.log_event(
            event_type='data_access',
            action=action,
            username=username,
            resource=resource,
            **details
        )

    def log_system_event(
        self,
        action: str,
        username: Optional[str] = None,
        level: AuditLevel = AuditLevel.INFO,
        **details
    ):
        """Log system event"""
        self.log_event(
            event_type='system',
            action=action,
            username=username,
            level=level,
            **details
        )

    def log_security_event(
        self,
        action: str,
        username: Optional[str] = None,
        level: AuditLevel = AuditLevel.CRITICAL,
        **details
    ):
        """Log security event"""
        self.log_event(
            event_type='security',
            action=action,
            username=username,
            level=level,
            **details
        )

    def get_events(
        self,
        event_type: Optional[str] = None,
        username: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        level: Optional[AuditLevel] = None,
    ) -> List[AuditEvent]:
        """
        Query audit events

        Args:
            event_type: Filter by event type
            username: Filter by username
            start_time: Filter by start time
            end_time: Filter by end time
            level: Filter by severity level

        Returns:
            List of matching events
        """
        results = self._events

        if event_type:
            results = [e for e in results if e.event_type == event_type]

        if username:
            results = [e for e in results if e.username == username]

        if start_time:
            results = [e for e in results if e.timestamp >= start_time]

        if end_time:
            results = [e for e in results if e.timestamp <= end_time]

        if level:
            results = [e for e in results if e.level == level]

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get audit statistics"""
        if not self._events:
            return {
                'total_events': 0,
                'by_type': {},
                'by_level': {},
                'by_result': {},
            }

        by_type = {}
        by_level = {}
        by_result = {}

        for event in self._events:
            by_type[event.event_type] = by_type.get(event.event_type, 0) + 1
            by_level[event.level.value] = by_level.get(event.level.value, 0) + 1
            by_result[event.result] = by_result.get(event.result, 0) + 1

        return {
            'total_events': len(self._events),
            'by_type': by_type,
            'by_level': by_level,
            'by_result': by_result,
        }


# Global audit logger
audit_logger = AuditLogger(log_file='audit.log')
