"""
Dependency Injection Container for OpenBenchVue

Provides inversion of control and dependency injection for better modularity
and testability.

Example:
    # Register services
    container = Container()
    container.register(DataLogger, singleton=True)
    container.register(InstrumentDetector)

    # Inject dependencies
    @inject
    def process_data(logger: DataLogger, detector: InstrumentDetector):
        # Dependencies automatically injected
        logger.log_data(...)

    # Or resolve manually
    logger = container.resolve(DataLogger)
"""

import inspect
import threading
from typing import Any, Callable, Dict, Optional, Type, TypeVar, get_type_hints
from functools import wraps
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class Lifetime:
    """Service lifetime enumeration"""
    SINGLETON = 'singleton'  # Single instance for entire application
    TRANSIENT = 'transient'  # New instance every time
    SCOPED = 'scoped'        # Single instance per scope


class ServiceDescriptor:
    """Describes a registered service"""

    def __init__(
        self,
        service_type: Type,
        implementation: Optional[Type] = None,
        factory: Optional[Callable] = None,
        instance: Optional[Any] = None,
        lifetime: str = Lifetime.TRANSIENT,
    ):
        """
        Create service descriptor

        Args:
            service_type: The interface/abstract type
            implementation: Concrete implementation class
            factory: Factory function to create instances
            instance: Pre-created instance (for singletons)
            lifetime: Service lifetime
        """
        self.service_type = service_type
        self.implementation = implementation or service_type
        self.factory = factory
        self.instance = instance
        self.lifetime = lifetime


class Container:
    """
    Dependency injection container

    Manages service registration and resolution with support for
    different lifetimes and automatic dependency injection.
    """

    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._lock = threading.RLock()
        self._scopes: Dict[str, Dict[Type, Any]] = {}

    def register(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None,
        instance: Optional[T] = None,
        lifetime: str = Lifetime.TRANSIENT,
    ) -> 'Container':
        """
        Register a service

        Args:
            service_type: Service interface/type
            implementation: Concrete implementation (if different from service_type)
            factory: Factory function to create instances
            instance: Pre-created instance (for singletons)
            lifetime: Service lifetime

        Returns:
            Self for chaining
        """
        with self._lock:
            if instance is not None:
                lifetime = Lifetime.SINGLETON

            descriptor = ServiceDescriptor(
                service_type=service_type,
                implementation=implementation,
                factory=factory,
                instance=instance,
                lifetime=lifetime,
            )

            self._services[service_type] = descriptor
            logger.debug(f"Registered {service_type.__name__} as {lifetime}")

        return self

    def register_singleton(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None,
        instance: Optional[T] = None,
    ) -> 'Container':
        """Register a singleton service"""
        return self.register(
            service_type,
            implementation=implementation,
            factory=factory,
            instance=instance,
            lifetime=Lifetime.SINGLETON,
        )

    def register_transient(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None,
    ) -> 'Container':
        """Register a transient service"""
        return self.register(
            service_type,
            implementation=implementation,
            factory=factory,
            lifetime=Lifetime.TRANSIENT,
        )

    def register_scoped(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None,
    ) -> 'Container':
        """Register a scoped service"""
        return self.register(
            service_type,
            implementation=implementation,
            factory=factory,
            lifetime=Lifetime.SCOPED,
        )

    def resolve(self, service_type: Type[T], scope: Optional[str] = None) -> T:
        """
        Resolve a service instance

        Args:
            service_type: Type of service to resolve
            scope: Scope name (for scoped services)

        Returns:
            Service instance

        Raises:
            KeyError: If service not registered
            TypeError: If service cannot be instantiated
        """
        with self._lock:
            if service_type not in self._services:
                raise KeyError(f"Service {service_type.__name__} not registered")

            descriptor = self._services[service_type]

            # Singleton: return cached instance
            if descriptor.lifetime == Lifetime.SINGLETON:
                if descriptor.instance is None:
                    descriptor.instance = self._create_instance(descriptor)
                return descriptor.instance

            # Scoped: return instance for this scope
            if descriptor.lifetime == Lifetime.SCOPED:
                if scope is None:
                    scope = 'default'

                if scope not in self._scopes:
                    self._scopes[scope] = {}

                if service_type not in self._scopes[scope]:
                    self._scopes[scope][service_type] = self._create_instance(descriptor)

                return self._scopes[scope][service_type]

            # Transient: always create new instance
            return self._create_instance(descriptor)

    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Create a new instance of a service"""
        # Use factory if provided
        if descriptor.factory:
            return descriptor.factory()

        # Auto-wire constructor dependencies
        impl = descriptor.implementation
        try:
            # Get constructor signature
            sig = inspect.signature(impl.__init__)
            type_hints = get_type_hints(impl.__init__)

            # Build kwargs for dependencies
            kwargs = {}
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue

                # Try to resolve dependency
                param_type = type_hints.get(param_name)
                if param_type and param_type in self._services:
                    kwargs[param_name] = self.resolve(param_type)
                elif param.default is not inspect.Parameter.empty:
                    # Has default value, skip
                    continue
                else:
                    # No type hint or not registered, skip
                    pass

            return impl(**kwargs)

        except Exception as e:
            logger.error(f"Error creating instance of {impl.__name__}: {e}")
            # Try without dependencies
            try:
                return impl()
            except Exception as e2:
                raise TypeError(
                    f"Cannot instantiate {impl.__name__}: {e2}"
                ) from e2

    def clear_scope(self, scope: str):
        """Clear a dependency scope"""
        with self._lock:
            if scope in self._scopes:
                del self._scopes[scope]

    def clear(self):
        """Clear all registrations and scopes"""
        with self._lock:
            self._services.clear()
            self._scopes.clear()

    def is_registered(self, service_type: Type) -> bool:
        """Check if a service is registered"""
        return service_type in self._services

    def get_registrations(self) -> Dict[str, str]:
        """Get all service registrations"""
        with self._lock:
            return {
                svc.__name__: desc.lifetime
                for svc, desc in self._services.items()
            }


# Global container instance
container = Container()


def inject(func: Callable) -> Callable:
    """
    Decorator to auto-inject dependencies into a function

    Dependencies are injected based on type hints.

    Example:
        @inject
        def process_data(logger: DataLogger, config: Config):
            # logger and config are automatically injected
            logger.log_data(...)
    """
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Resolve dependencies
        bound = sig.bind_partial(*args, **kwargs)

        for param_name, param in sig.parameters.items():
            if param_name in bound.arguments:
                continue  # Already provided

            # Try to resolve from container
            param_type = type_hints.get(param_name)
            if param_type and container.is_registered(param_type):
                bound.arguments[param_name] = container.resolve(param_type)

        return func(*bound.args, **bound.kwargs)

    return wrapper


def singleton(cls: Type[T]) -> Type[T]:
    """
    Class decorator to register a class as a singleton

    Example:
        @singleton
        class DataLogger:
            pass
    """
    container.register_singleton(cls)
    return cls


def transient(cls: Type[T]) -> Type[T]:
    """
    Class decorator to register a class as transient

    Example:
        @transient
        class TemporaryProcessor:
            pass
    """
    container.register_transient(cls)
    return cls
