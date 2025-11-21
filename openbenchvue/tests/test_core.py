"""
Tests for core architecture components
"""

import pytest
import time
from openbenchvue.core import (
    PluginManager,
    Plugin,
    PluginMetadata,
    EventBus,
    Event,
    Container,
    inject,
    singleton,
)


class TestPluginManager:
    """Tests for plugin system"""

    def test_plugin_registration(self):
        """Test plugin registration"""
        manager = PluginManager()

        class TestPlugin(Plugin):
            metadata = PluginMetadata(
                name="test_plugin",
                version="1.0.0",
                author="Test",
                description="Test plugin",
                plugin_type="test",
            )

            def initialize(self, config):
                return True

        plugin = TestPlugin()
        assert manager.register(plugin)
        assert "test_plugin" in manager.plugins

    def test_plugin_unregistration(self):
        """Test plugin unregistration"""
        manager = PluginManager()

        class TestPlugin(Plugin):
            metadata = PluginMetadata(
                name="test_plugin",
                version="1.0.0",
                author="Test",
                description="Test plugin",
                plugin_type="test",
            )

            def initialize(self, config):
                return True

        plugin = TestPlugin()
        manager.register(plugin)
        assert manager.unregister("test_plugin")
        assert "test_plugin" not in manager.plugins

    def test_plugin_dependencies(self):
        """Test plugin dependency checking"""
        manager = PluginManager()

        class BasePlugin(Plugin):
            metadata = PluginMetadata(
                name="base_plugin",
                version="1.0.0",
                author="Test",
                description="Base plugin",
                plugin_type="test",
            )

            def initialize(self, config):
                return True

        class DependentPlugin(Plugin):
            metadata = PluginMetadata(
                name="dependent_plugin",
                version="1.0.0",
                author="Test",
                description="Dependent plugin",
                plugin_type="test",
                dependencies=["base_plugin"],
            )

            def initialize(self, config):
                return True

        # Should fail without dependency
        dependent = DependentPlugin()
        assert not manager.register(dependent)

        # Should succeed with dependency
        base = BasePlugin()
        manager.register(base)
        assert manager.register(dependent)

    def test_get_plugins_by_type(self):
        """Test getting plugins by type"""
        manager = PluginManager()

        class Plugin1(Plugin):
            metadata = PluginMetadata(
                name="plugin1",
                version="1.0.0",
                author="Test",
                description="Plugin 1",
                plugin_type="type_a",
            )

            def initialize(self, config):
                return True

        class Plugin2(Plugin):
            metadata = PluginMetadata(
                name="plugin2",
                version="1.0.0",
                author="Test",
                description="Plugin 2",
                plugin_type="type_b",
            )

            def initialize(self, config):
                return True

        manager.register(Plugin1())
        manager.register(Plugin2())

        type_a_plugins = manager.get_plugins_by_type("type_a")
        assert len(type_a_plugins) == 1
        assert type_a_plugins[0].metadata.name == "plugin1"


class TestEventBus:
    """Tests for event bus"""

    def test_publish_subscribe(self):
        """Test basic publish/subscribe"""
        bus = EventBus(async_mode=False)
        received_events = []

        def handler(event):
            received_events.append(event)

        bus.subscribe("test.event", handler)
        bus.emit("test.event", data="test data")

        assert len(received_events) == 1
        assert received_events[0].type == "test.event"
        assert received_events[0].data == "test data"

    def test_wildcard_patterns(self):
        """Test wildcard event patterns"""
        bus = EventBus(async_mode=False)
        received_events = []

        def handler(event):
            received_events.append(event)

        bus.subscribe("measurement.*", handler)
        bus.emit("measurement.new", data=1)
        bus.emit("measurement.updated", data=2)
        bus.emit("other.event", data=3)

        assert len(received_events) == 2

    def test_priority_handling(self):
        """Test handler priority"""
        bus = EventBus(async_mode=False)
        call_order = []

        def handler1(event):
            call_order.append(1)

        def handler2(event):
            call_order.append(2)

        bus.subscribe("test", handler1, priority=100)
        bus.subscribe("test", handler2, priority=50)
        bus.emit("test")

        assert call_order == [2, 1]  # Lower priority number called first

    def test_once_subscription(self):
        """Test one-time subscriptions"""
        bus = EventBus(async_mode=False)
        call_count = [0]

        def handler(event):
            call_count[0] += 1

        bus.subscribe("test", handler, once=True)
        bus.emit("test")
        bus.emit("test")

        assert call_count[0] == 1  # Only called once

    def test_filter_function(self):
        """Test event filtering"""
        bus = EventBus(async_mode=False)
        received = []

        def handler(event):
            received.append(event.data)

        bus.subscribe(
            "measurement",
            handler,
            filter_fn=lambda e: e.data > 5
        )

        bus.emit("measurement", data=3)
        bus.emit("measurement", data=7)
        bus.emit("measurement", data=10)

        assert received == [7, 10]

    def test_async_mode(self):
        """Test asynchronous event processing"""
        bus = EventBus(async_mode=True)
        received = []

        def handler(event):
            received.append(event.data)

        bus.subscribe("test", handler)
        bus.emit("test", data="async")

        # Wait for async processing
        bus.wait_for_events()

        assert len(received) == 1
        bus.shutdown()


class TestDependencyInjection:
    """Tests for dependency injection"""

    def test_singleton_registration(self):
        """Test singleton service registration"""
        container = Container()

        class TestService:
            def __init__(self):
                self.value = time.time()

        container.register_singleton(TestService)

        instance1 = container.resolve(TestService)
        instance2 = container.resolve(TestService)

        assert instance1 is instance2  # Same instance

    def test_transient_registration(self):
        """Test transient service registration"""
        container = Container()

        class TestService:
            def __init__(self):
                self.value = time.time()

        container.register_transient(TestService)

        instance1 = container.resolve(TestService)
        time.sleep(0.001)
        instance2 = container.resolve(TestService)

        assert instance1 is not instance2  # Different instances
        assert instance1.value != instance2.value

    def test_dependency_autowiring(self):
        """Test automatic dependency injection"""
        container = Container()

        class DependencyService:
            def __init__(self):
                self.name = "dependency"

        class MainService:
            def __init__(self, dependency: DependencyService):
                self.dependency = dependency

        container.register_singleton(DependencyService)
        container.register_transient(MainService)

        instance = container.resolve(MainService)
        assert isinstance(instance.dependency, DependencyService)
        assert instance.dependency.name == "dependency"

    def test_inject_decorator(self):
        """Test @inject decorator"""
        container = Container()

        class TestService:
            def __init__(self):
                self.value = 42

        container.register_singleton(TestService)

        @inject
        def process(service: TestService):
            return service.value

        result = process()
        assert result == 42

    def test_singleton_decorator(self):
        """Test @singleton decorator"""
        container2 = Container()

        @singleton
        class SingletonService:
            def __init__(self):
                self.value = time.time()

        # Note: decorator registers in global container
        from openbenchvue.core.dependency_injection import container as global_container

        instance1 = global_container.resolve(SingletonService)
        instance2 = global_container.resolve(SingletonService)

        assert instance1 is instance2

    def test_scoped_services(self):
        """Test scoped service lifetime"""
        container = Container()

        class ScopedService:
            def __init__(self):
                self.value = time.time()

        container.register_scoped(ScopedService)

        # Same instance within scope
        instance1 = container.resolve(ScopedService, scope="scope1")
        instance2 = container.resolve(ScopedService, scope="scope1")
        assert instance1 is instance2

        # Different instance in different scope
        instance3 = container.resolve(ScopedService, scope="scope2")
        assert instance1 is not instance3

    def test_factory_function(self):
        """Test factory function registration"""
        container = Container()

        class TestService:
            def __init__(self, value):
                self.value = value

        def factory():
            return TestService(value=100)

        container.register(TestService, factory=factory)

        instance = container.resolve(TestService)
        assert instance.value == 100
