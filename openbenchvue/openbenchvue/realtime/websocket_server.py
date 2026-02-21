"""
WebSocket Server with Socket.IO

Real-time bidirectional communication for live updates and collaboration.
"""

import logging
from typing import Dict, Any, Optional, Callable, List
import socketio
from aiohttp import web
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)


class WebSocketServer:
    """Socket.IO-based WebSocket server for real-time communication"""

    def __init__(
        self,
        host: str = '0.0.0.0',
        port: int = 8000,
        cors_allowed_origins: str = '*',
        async_mode: str = 'aiohttp',
    ):
        """
        Initialize WebSocket server

        Args:
            host: Server host
            port: Server port
            cors_allowed_origins: CORS allowed origins
            async_mode: Async mode ('aiohttp', 'threading', etc.)
        """
        self.host = host
        self.port = port

        # Create Socket.IO server
        self.sio = socketio.AsyncServer(
            async_mode=async_mode,
            cors_allowed_origins=cors_allowed_origins,
            logger=False,
            engineio_logger=False,
            ping_timeout=60,
            ping_interval=25,
        )

        # Create web application
        self.app = web.Application()
        self.sio.attach(self.app)

        # Connected clients
        self.clients: Dict[str, Dict[str, Any]] = {}  # sid -> client info

        # Event handlers
        self._event_handlers: Dict[str, List[Callable]] = {}

        # Register default event handlers
        self._register_default_handlers()

        # Server task
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None

    def _register_default_handlers(self):
        """Register default Socket.IO event handlers"""

        @self.sio.event
        async def connect(sid, environ):
            """Handle client connection"""
            client_info = {
                'sid': sid,
                'connected_at': datetime.utcnow(),
                'rooms': [],
                'user_id': None,
                'username': None,
                'metadata': {}
            }
            self.clients[sid] = client_info
            logger.info(f"Client connected: {sid}")

            # Emit connected event
            await self.sio.emit('connected', {
                'sid': sid,
                'timestamp': datetime.utcnow().isoformat()
            }, room=sid)

        @self.sio.event
        async def disconnect(sid):
            """Handle client disconnection"""
            if sid in self.clients:
                logger.info(f"Client disconnected: {sid}")
                del self.clients[sid]

        @self.sio.event
        async def authenticate(sid, data):
            """Handle client authentication"""
            if sid not in self.clients:
                return {'success': False, 'error': 'Invalid session'}

            # Extract credentials
            token = data.get('token')
            if not token:
                return {'success': False, 'error': 'No token provided'}

            # TODO: Validate token with authentication manager
            # For now, just store user info
            self.clients[sid]['user_id'] = data.get('user_id')
            self.clients[sid]['username'] = data.get('username')
            self.clients[sid]['authenticated'] = True

            logger.info(f"Client authenticated: {sid} ({self.clients[sid]['username']})")

            return {'success': True, 'message': 'Authenticated successfully'}

        @self.sio.event
        async def join_room(sid, data):
            """Join a room (e.g., instrument channel)"""
            room = data.get('room')
            if not room:
                return {'success': False, 'error': 'No room specified'}

            self.sio.enter_room(sid, room)
            if sid in self.clients:
                self.clients[sid]['rooms'].append(room)

            logger.debug(f"Client {sid} joined room: {room}")

            # Notify room members
            await self.sio.emit('user_joined', {
                'sid': sid,
                'username': self.clients.get(sid, {}).get('username'),
                'room': room,
                'timestamp': datetime.utcnow().isoformat()
            }, room=room, skip_sid=sid)

            return {'success': True, 'room': room}

        @self.sio.event
        async def leave_room(sid, data):
            """Leave a room"""
            room = data.get('room')
            if not room:
                return {'success': False, 'error': 'No room specified'}

            self.sio.leave_room(sid, room)
            if sid in self.clients and room in self.clients[sid]['rooms']:
                self.clients[sid]['rooms'].remove(room)

            logger.debug(f"Client {sid} left room: {room}")

            # Notify room members
            await self.sio.emit('user_left', {
                'sid': sid,
                'username': self.clients.get(sid, {}).get('username'),
                'room': room,
                'timestamp': datetime.utcnow().isoformat()
            }, room=room)

            return {'success': True, 'room': room}

        @self.sio.event
        async def ping(sid):
            """Handle ping (for keep-alive)"""
            return {'pong': datetime.utcnow().isoformat()}

    async def start(self):
        """Start WebSocket server"""
        try:
            logger.info(f"Starting WebSocket server on {self.host}:{self.port}")

            self._runner = web.AppRunner(self.app)
            await self._runner.setup()

            self._site = web.TCPSite(self._runner, self.host, self.port)
            await self._site.start()

            logger.info(f"WebSocket server started successfully")
            logger.info(f"WebSocket URL: ws://{self.host}:{self.port}")

        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            raise

    async def stop(self):
        """Stop WebSocket server"""
        try:
            logger.info("Stopping WebSocket server...")

            if self._site:
                await self._site.stop()

            if self._runner:
                await self._runner.cleanup()

            logger.info("WebSocket server stopped")

        except Exception as e:
            logger.error(f"Error stopping WebSocket server: {e}")

    async def emit(
        self,
        event: str,
        data: Any,
        room: Optional[str] = None,
        skip_sid: Optional[str] = None
    ):
        """
        Emit event to clients

        Args:
            event: Event name
            data: Event data
            room: Optional room name (broadcast to room)
            skip_sid: Optional SID to skip
        """
        await self.sio.emit(event, data, room=room, skip_sid=skip_sid)

    async def emit_to_user(self, username: str, event: str, data: Any):
        """
        Emit event to specific user

        Args:
            username: Target username
            event: Event name
            data: Event data
        """
        for sid, client in self.clients.items():
            if client.get('username') == username:
                await self.sio.emit(event, data, room=sid)

    async def broadcast(self, event: str, data: Any):
        """
        Broadcast event to all connected clients

        Args:
            event: Event name
            data: Event data
        """
        await self.sio.emit(event, data)

    def on_event(self, event_name: str):
        """
        Decorator to register custom event handler

        Usage:
            @ws_server.on_event('custom_event')
            async def handle_custom(sid, data):
                return {'status': 'ok'}
        """
        def decorator(handler):
            self.sio.on(event_name, handler)
            return handler
        return decorator

    def get_connected_clients(self) -> List[Dict[str, Any]]:
        """Get list of connected clients"""
        return [
            {
                'sid': sid,
                'username': client.get('username'),
                'connected_at': client.get('connected_at').isoformat() if client.get('connected_at') else None,
                'rooms': client.get('rooms', []),
                'authenticated': client.get('authenticated', False)
            }
            for sid, client in self.clients.items()
        ]

    def get_room_members(self, room: str) -> List[str]:
        """Get list of clients in a room"""
        members = []
        for sid, client in self.clients.items():
            if room in client.get('rooms', []):
                members.append(sid)
        return members

    def get_client_count(self) -> int:
        """Get number of connected clients"""
        return len(self.clients)


# ============================================================================
# Event Channel Constants
# ============================================================================

class Channels:
    """WebSocket channel/room names"""

    # Instrument channels
    INSTRUMENT_PREFIX = 'instrument:'  # instrument:INSTRUMENT_ID
    INSTRUMENT_ALL = 'instruments:all'

    # Measurement channels
    MEASUREMENT_PREFIX = 'measurement:'  # measurement:INSTRUMENT_ID
    MEASUREMENT_ALL = 'measurements:all'

    # Automation channels
    AUTOMATION_PREFIX = 'automation:'  # automation:SEQUENCE_ID
    AUTOMATION_ALL = 'automation:all'

    # System channels
    SYSTEM_ALERTS = 'system:alerts'
    SYSTEM_STATUS = 'system:status'

    # User presence
    PRESENCE = 'presence'

    @staticmethod
    def instrument(instrument_id: int) -> str:
        """Get instrument channel name"""
        return f"{Channels.INSTRUMENT_PREFIX}{instrument_id}"

    @staticmethod
    def measurement(instrument_id: int) -> str:
        """Get measurement channel name"""
        return f"{Channels.MEASUREMENT_PREFIX}{instrument_id}"

    @staticmethod
    def automation(sequence_id: int) -> str:
        """Get automation channel name"""
        return f"{Channels.AUTOMATION_PREFIX}{sequence_id}"


class Events:
    """WebSocket event names"""

    # Connection events
    CONNECTED = 'connected'
    DISCONNECTED = 'disconnected'
    AUTHENTICATED = 'authenticated'

    # Measurement events
    MEASUREMENT_NEW = 'measurement:new'
    MEASUREMENT_BATCH = 'measurement:batch'

    # Instrument events
    INSTRUMENT_CONNECTED = 'instrument:connected'
    INSTRUMENT_DISCONNECTED = 'instrument:disconnected'
    INSTRUMENT_STATUS = 'instrument:status'
    INSTRUMENT_ERROR = 'instrument:error'

    # Automation events
    SEQUENCE_STARTED = 'sequence:started'
    SEQUENCE_PROGRESS = 'sequence:progress'
    SEQUENCE_COMPLETED = 'sequence:completed'
    SEQUENCE_FAILED = 'sequence:failed'
    SEQUENCE_PAUSED = 'sequence:paused'

    # Anomaly events
    ANOMALY_DETECTED = 'anomaly:detected'

    # Alert events
    ALERT_WARNING = 'alert:warning'
    ALERT_ERROR = 'alert:error'
    ALERT_CRITICAL = 'alert:critical'

    # User presence
    USER_JOINED = 'user:joined'
    USER_LEFT = 'user:left'
    USER_ONLINE = 'user:online'
    USER_OFFLINE = 'user:offline'

    # System events
    SYSTEM_STATUS = 'system:status'
    SYSTEM_MAINTENANCE = 'system:maintenance'


# ============================================================================
# Global WebSocket Server Instance
# ============================================================================

_ws_server: Optional[WebSocketServer] = None


def get_websocket_server() -> WebSocketServer:
    """Get global WebSocket server instance"""
    global _ws_server
    if _ws_server is None:
        raise RuntimeError("WebSocket server not initialized")
    return _ws_server


def init_websocket_server(
    host: str = '0.0.0.0',
    port: int = 8000,
    cors_allowed_origins: str = '*'
) -> WebSocketServer:
    """Initialize global WebSocket server"""
    global _ws_server

    if _ws_server is not None:
        logger.warning("WebSocket server already initialized")
        return _ws_server

    _ws_server = WebSocketServer(
        host=host,
        port=port,
        cors_allowed_origins=cors_allowed_origins
    )

    return _ws_server


async def shutdown_websocket_server():
    """Shutdown global WebSocket server"""
    global _ws_server

    if _ws_server is not None:
        await _ws_server.stop()
        _ws_server = None
