"""
Event-Driven Architecture for OpenBenchVue

Provides a publish-subscribe event bus for decoupled communication
between components.

Example:
    # Subscribe to events
    def on_measurement(event):
        print(f"New measurement: {event.data['value']}")

    event_bus.subscribe('measurement.new', on_measurement)

    # Publish events
    event_bus.publish(Event('measurement.new', {'value': 3.14, 'unit': 'V'}))

    # Use event filters
    event_bus.subscribe(
        'measurement.*',
        on_any_measurement,
        filter_fn=lambda e: e.data.get('value', 0) > 5.0
    )
"""

import threading
import queue
import fnmatch
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
import logging
import weakref

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """
    Represents an event in the system

    Events have a type (e.g., 'instrument.connected'), data payload,
    and metadata like timestamp and source.
    """
    type: str
    data: Any = None
    timestamp: datetime = field(default_factory=datetime.now)
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def matches_pattern(self, pattern: str) -> bool:
        """Check if event type matches a pattern (supports wildcards)"""
        return fnmatch.fnmatch(self.type, pattern)


class EventHandler:
    """
    Wraps an event handler callback with metadata

    Handlers can have priority, filters, and other options.
    """

    def __init__(
        self,
        callback: Callable[[Event], None],
        pattern: str,
        priority: int = 100,
        filter_fn: Optional[Callable[[Event], bool]] = None,
        once: bool = False,
        weak: bool = False,
    ):
        """
        Create event handler

        Args:
            callback: Function to call when event occurs
            pattern: Event type pattern (supports wildcards like 'measurement.*')
            priority: Handler priority (lower = higher priority)
            filter_fn: Optional filter function
            once: If True, handler is removed after first invocation
            weak: If True, use weak reference to callback
        """
        if weak:
            # Use weak reference to avoid keeping objects alive
            self._callback_ref = weakref.ref(callback)
        else:
            self._callback_ref = lambda: callback

        self.pattern = pattern
        self.priority = priority
        self.filter_fn = filter_fn
        self.once = once
        self.call_count = 0
        self.last_called = None

    @property
    def callback(self) -> Optional[Callable]:
        """Get the callback function (may return None if weak ref is dead)"""
        return self._callback_ref()

    def matches(self, event: Event) -> bool:
        """Check if this handler matches an event"""
        if not event.matches_pattern(self.pattern):
            return False

        if self.filter_fn and not self.filter_fn(event):
            return False

        return True

    def handle(self, event: Event):
        """Handle an event"""
        callback = self.callback
        if callback is None:
            return  # Weak reference is dead

        try:
            callback(event)
            self.call_count += 1
            self.last_called = datetime.now()
        except Exception as e:
            logger.error(f"Error in event handler for {self.pattern}: {e}")


class EventBus:
    """
    Central event bus for publish-subscribe messaging

    The event bus allows components to communicate without direct dependencies.
    Components publish events and subscribe to events they're interested in.
    """

    def __init__(self, async_mode: bool = False, max_queue_size: int = 1000):
        """
        Initialize event bus

        Args:
            async_mode: If True, events are processed asynchronously
            max_queue_size: Maximum size of async event queue
        """
        self._handlers: List[EventHandler] = []
        self._lock = threading.RLock()
        self._async_mode = async_mode
        self._event_queue: Optional[queue.Queue] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False
        self._stats = {
            'events_published': 0,
            'events_handled': 0,
            'errors': 0,
        }

        if async_mode:
            self._event_queue = queue.Queue(maxsize=max_queue_size)
            self._start_worker()

    def subscribe(
        self,
        pattern: str,
        callback: Callable[[Event], None],
        priority: int = 100,
        filter_fn: Optional[Callable[[Event], bool]] = None,
        once: bool = False,
        weak: bool = False,
    ) -> EventHandler:
        """
        Subscribe to events

        Args:
            pattern: Event type pattern (e.g., 'measurement.*')
            callback: Function to call when event occurs
            priority: Handler priority (lower number = higher priority)
            filter_fn: Optional filter function
            once: If True, unsubscribe after first event
            weak: If True, use weak reference to callback

        Returns:
            EventHandler instance (can be used to unsubscribe)
        """
        handler = EventHandler(
            callback=callback,
            pattern=pattern,
            priority=priority,
            filter_fn=filter_fn,
            once=once,
            weak=weak,
        )

        with self._lock:
            self._handlers.append(handler)
            self._handlers.sort(key=lambda h: h.priority)

        logger.debug(f"Subscribed to {pattern}")
        return handler

    def unsubscribe(self, handler: EventHandler):
        """
        Unsubscribe an event handler

        Args:
            handler: EventHandler instance returned by subscribe()
        """
        with self._lock:
            if handler in self._handlers:
                self._handlers.remove(handler)
                logger.debug(f"Unsubscribed from {handler.pattern}")

    def unsubscribe_all(self, pattern: Optional[str] = None):
        """
        Unsubscribe all handlers, optionally filtered by pattern

        Args:
            pattern: If provided, only unsubscribe handlers matching this pattern
        """
        with self._lock:
            if pattern is None:
                count = len(self._handlers)
                self._handlers.clear()
                logger.info(f"Unsubscribed all {count} handlers")
            else:
                original_count = len(self._handlers)
                self._handlers = [
                    h for h in self._handlers
                    if h.pattern != pattern
                ]
                removed = original_count - len(self._handlers)
                logger.info(f"Unsubscribed {removed} handlers for {pattern}")

    def publish(self, event: Event, wait: bool = True):
        """
        Publish an event

        Args:
            event: Event to publish
            wait: In async mode, whether to wait if queue is full
        """
        self._stats['events_published'] += 1

        if self._async_mode and self._event_queue:
            try:
                self._event_queue.put(event, block=wait, timeout=1.0)
            except queue.Full:
                logger.warning(f"Event queue full, dropping event: {event.type}")
        else:
            self._process_event(event)

    def emit(self, event_type: str, data: Any = None, **kwargs):
        """
        Convenience method to publish an event

        Args:
            event_type: Type of event
            data: Event data
            **kwargs: Additional event properties
        """
        event = Event(type=event_type, data=data, **kwargs)
        self.publish(event)

    def _process_event(self, event: Event):
        """Process an event by calling matching handlers"""
        handlers_to_remove = []

        with self._lock:
            handlers = list(self._handlers)  # Copy to avoid modification during iteration

        for handler in handlers:
            if handler.matches(event):
                handler.handle(event)
                self._stats['events_handled'] += 1

                if handler.once:
                    handlers_to_remove.append(handler)

                # Check if weak reference is dead
                if handler.callback is None:
                    handlers_to_remove.append(handler)

        # Remove one-time and dead handlers
        if handlers_to_remove:
            with self._lock:
                for handler in handlers_to_remove:
                    if handler in self._handlers:
                        self._handlers.remove(handler)

    def _start_worker(self):
        """Start async event processing worker thread"""
        self._running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="EventBusWorker"
        )
        self._worker_thread.start()
        logger.info("Event bus worker started")

    def _worker_loop(self):
        """Worker thread main loop"""
        while self._running:
            try:
                event = self._event_queue.get(timeout=0.1)
                self._process_event(event)
                self._event_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in event bus worker: {e}")
                self._stats['errors'] += 1

    def shutdown(self):
        """Shutdown the event bus"""
        if self._async_mode:
            self._running = False
            if self._worker_thread:
                self._worker_thread.join(timeout=2.0)
            logger.info("Event bus worker stopped")

        self.unsubscribe_all()

    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        with self._lock:
            return {
                **self._stats,
                'handlers_registered': len(self._handlers),
                'async_mode': self._async_mode,
                'queue_size': self._event_queue.qsize() if self._event_queue else 0,
            }

    def wait_for_events(self, timeout: Optional[float] = None):
        """
        Wait for all queued events to be processed (async mode only)

        Args:
            timeout: Maximum time to wait in seconds
        """
        if self._event_queue:
            self._event_queue.join()


# Global event bus instance
event_bus = EventBus(async_mode=True)
