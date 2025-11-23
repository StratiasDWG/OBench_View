#!/usr/bin/env python3
"""
Deep Analysis and Testing Script for OpenBenchVue Design Enhancements

This script performs comprehensive analysis to identify:
- Import issues and circular dependencies
- Missing implementations
- API inconsistencies
- Thread safety issues
- Integration problems
- Configuration issues
"""

import sys
import os
sys.path.insert(0, '.')

def test_imports():
    """Test all module imports"""
    print("=" * 80)
    print("TESTING IMPORTS")
    print("=" * 80)

    tests = [
        ("Core - PluginManager", "from openbenchvue.core import PluginManager"),
        ("Core - EventBus", "from openbenchvue.core import EventBus"),
        ("Core - Container", "from openbenchvue.core import Container"),
        ("Core - plugin_manager (global)", "from openbenchvue.core import plugin_manager"),
        ("Core - event_bus (global)", "from openbenchvue.core import event_bus"),
        ("Core - container (global)", "from openbenchvue.core import container"),
        ("Security - AuthenticationManager", "from openbenchvue.security import AuthenticationManager"),
        ("Security - AuthorizationManager", "from openbenchvue.security import AuthorizationManager"),
        ("Security - authz_manager (global)", "from openbenchvue.security import authz_manager"),
        ("Security - audit_logger (global)", "from openbenchvue.security import audit_logger"),
        ("Main package", "import openbenchvue"),
    ]

    passed = 0
    failed = 0

    for name, import_stmt in tests:
        try:
            exec(import_stmt)
            print(f"✓ {name}")
            passed += 1
        except Exception as e:
            print(f"✗ {name}: {e}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed\n")
    return failed == 0


def test_global_instances():
    """Test that global instances are properly created"""
    print("=" * 80)
    print("TESTING GLOBAL INSTANCES")
    print("=" * 80)

    try:
        from openbenchvue.core import plugin_manager, event_bus, container
        print(f"✓ plugin_manager: {type(plugin_manager).__name__}")
        print(f"✓ event_bus: {type(event_bus).__name__}")
        print(f"✓ container: {type(container).__name__}")

        from openbenchvue.security import authz_manager, audit_logger
        print(f"✓ authz_manager: {type(authz_manager).__name__}")
        print(f"✓ audit_logger: {type(audit_logger).__name__}")

        print("\n✓ All global instances created successfully\n")
        return True
    except Exception as e:
        print(f"✗ Global instances test failed: {e}\n")
        return False


def test_basic_functionality():
    """Test basic functionality of core components"""
    print("=" * 80)
    print("TESTING BASIC FUNCTIONALITY")
    print("=" * 80)

    try:
        # Test Event Bus
        from openbenchvue.core import EventBus, Event
        bus = EventBus(async_mode=False)

        received = []
        bus.subscribe("test", lambda e: received.append(e.data))
        bus.emit("test", data="hello")

        assert len(received) == 1
        assert received[0] == "hello"
        print("✓ Event Bus: publish/subscribe works")

        # Test Container
        from openbenchvue.core import Container
        container = Container()

        class TestService:
            def __init__(self):
                self.value = 42

        container.register_singleton(TestService)
        instance = container.resolve(TestService)
        assert instance.value == 42
        print("✓ Container: service registration and resolution works")

        # Test Plugin Manager
        from openbenchvue.core import PluginManager, Plugin, PluginMetadata

        class TestPlugin(Plugin):
            metadata = PluginMetadata(
                name="test",
                version="1.0.0",
                author="test",
                description="test plugin",
                plugin_type="test"
            )

            def initialize(self, config):
                return True

        manager = PluginManager()
        plugin = TestPlugin()
        assert manager.register(plugin)
        print("✓ Plugin Manager: plugin registration works")

        # Test Authentication
        from openbenchvue.security import AuthenticationManager
        auth = AuthenticationManager()

        auth.register_user("testuser", "TestPass123!", email="test@example.com")
        token = auth.login("testuser", "TestPass123!")
        assert token is not None
        print("✓ Authentication: user registration and login works")

        # Test Authorization
        from openbenchvue.security import AuthorizationManager, Permission
        authz = AuthorizationManager()

        has_perm = authz.check_permission(['user'], Permission.INSTRUMENT_VIEW)
        assert has_perm
        print("✓ Authorization: permission checking works")

        # Test Audit Logger
        from openbenchvue.security import AuditLogger
        audit = AuditLogger()

        audit.log_authentication("login", "testuser", "success")
        events = audit.get_events(event_type="authentication")
        assert len(events) > 0
        print("✓ Audit Logger: event logging works")

        print("\n✓ All basic functionality tests passed\n")
        return True

    except Exception as e:
        print(f"✗ Basic functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def test_api_consistency():
    """Test API consistency across modules"""
    print("=" * 80)
    print("TESTING API CONSISTENCY")
    print("=" * 80)

    issues = []

    # Check that all managers have consistent method naming
    try:
        from openbenchvue.security import AuthenticationManager, AuthorizationManager

        auth = AuthenticationManager()
        authz = AuthorizationManager()

        # Both should have consistent patterns
        if not hasattr(auth, 'get_user'):
            issues.append("AuthenticationManager missing get_user method")

        if not hasattr(authz, 'get_role'):
            issues.append("AuthorizationManager missing get_role method")

    except Exception as e:
        issues.append(f"API consistency check failed: {e}")

    if issues:
        for issue in issues:
            print(f"⚠ {issue}")
        print()
    else:
        print("✓ API consistency check passed\n")

    return len(issues) == 0


def check_thread_safety():
    """Check for thread safety issues"""
    print("=" * 80)
    print("CHECKING THREAD SAFETY")
    print("=" * 80)

    issues = []

    # Check that critical sections use locks
    import inspect
    from openbenchvue.core import PluginManager, EventBus, Container

    # PluginManager should have locks
    pm = PluginManager()
    if not hasattr(pm, '_lock'):
        issues.append("PluginManager missing thread lock")

    # EventBus should have locks
    from openbenchvue.core import event_bus
    if not hasattr(event_bus, '_lock'):
        issues.append("EventBus missing thread lock")

    # Container should have locks
    from openbenchvue.core import container
    if not hasattr(container, '_lock'):
        issues.append("Container missing thread lock")

    if issues:
        for issue in issues:
            print(f"⚠ {issue}")
        print()
    else:
        print("✓ Thread safety checks passed\n")

    return len(issues) == 0


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("DEEP ANALYSIS OF OPENBENCHVUE DESIGN ENHANCEMENTS")
    print("=" * 80 + "\n")

    results = {
        "Imports": test_imports(),
        "Global Instances": test_global_instances(),
        "Basic Functionality": test_basic_functionality(),
        "API Consistency": test_api_consistency(),
        "Thread Safety": check_thread_safety(),
    }

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name}: {status}")

    all_passed = all(results.values())

    print("\n" + "=" * 80)
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED - REVIEW NEEDED")
    print("=" * 80 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
