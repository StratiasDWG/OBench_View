"""
Real-time Communication Package

WebSocket-based real-time communication for live updates and collaboration.

Features:
- Socket.IO for cross-platform support
- Room-based messaging
- User presence tracking
- Real-time measurement streaming
- Live automation updates
- Alert notifications
"""

from .websocket_server import (
    WebSocketServer,
    Channels,
    Events,
    get_websocket_server,
    init_websocket_server,
    shutdown_websocket_server,
)

__all__ = [
    'WebSocketServer',
    'Channels',
    'Events',
    'get_websocket_server',
    'init_websocket_server',
    'shutdown_websocket_server',
]
