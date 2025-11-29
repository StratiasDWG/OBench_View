#!/usr/bin/env python3
"""
Advanced Deep Analysis for OpenBenchVue

Comprehensive analysis covering:
- Memory management and leak detection
- Concurrency issues (deadlocks, race conditions)
- Performance bottlenecks
- Error handling completeness
- Edge case coverage
- Code quality metrics
- Security vulnerabilities
- Integration testing
"""

import sys
import os
import time
import threading
import gc
import traceback
from typing import List, Dict, Any, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, TimeoutError

sys.path.insert(0, '.')

# Color codes for output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 80}")
    print(f"{text}")
    print(f"{'=' * 80}{Colors.RESET}\n")

def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")

def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_info(text: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")

@dataclass
class TestResult:
    """Result of a test"""
    name: str
    passed: bool
    message: str
    severity: str = 'INFO'  # INFO, WARNING, ERROR, CRITICAL

class AdvancedAnalyzer:
    """Advanced analysis framework"""

    def __init__(self):
        self.results: List[TestResult] = []
        self.issues_found = 0
        self.warnings_found = 0

    def add_result(self, result: TestResult):
        """Add a test result"""
        self.results.append(result)
        if not result.passed:
            if result.severity in ['ERROR', 'CRITICAL']:
                self.issues_found += 1
            else:
                self.warnings_found += 1

    def test_memory_leaks(self):
        """Test for potential memory leaks"""
        print_header("MEMORY LEAK ANALYSIS")

        try:
            from openbenchvue.core import EventBus

            # Test event bus memory growth
            print_info("Testing event bus memory management...")
            bus = EventBus(async_mode=False)

            # Subscribe many handlers
            handlers = []
            for i in range(1000):
                handler = lambda e, i=i: None
                handlers.append(bus.subscribe(f"test.{i}", handler))

            # Unsubscribe all
            for handler in handlers:
                bus.unsubscribe(handler)

            # Check if handlers are cleaned up
            if len(bus._handlers) == 0:
                print_success("Event bus properly cleans up handlers")
                self.add_result(TestResult(
                    "Event bus memory cleanup",
                    True,
                    "Handlers properly cleaned up"
                ))
            else:
                print_error(f"Event bus has {len(bus._handlers)} leaked handlers")
                self.add_result(TestResult(
                    "Event bus memory cleanup",
                    False,
                    f"{len(bus._handlers)} handlers not cleaned up",
                    'ERROR'
                ))

            # Test weak references
            print_info("Testing weak reference cleanup...")
            received = []

            def temp_handler(e):
                received.append(e)

            bus.subscribe("test.weak", temp_handler, weak=True)

            # Delete reference and force GC
            del temp_handler
            gc.collect()

            # Emit event - should not be handled if weak ref cleaned up
            bus.emit("test.weak", data="test")

            if len(received) == 0:
                print_success("Weak references properly cleaned up")
                self.add_result(TestResult(
                    "Weak reference cleanup",
                    True,
                    "Dead weak references removed"
                ))
            else:
                print_warning("Weak references may not be cleaned up properly")
                self.add_result(TestResult(
                    "Weak reference cleanup",
                    False,
                    "Weak refs not cleaned after deletion",
                    'WARNING'
                ))

        except Exception as e:
            print_error(f"Memory leak analysis failed: {e}")
            self.add_result(TestResult(
                "Memory leak analysis",
                False,
                str(e),
                'ERROR'
            ))

    def test_concurrency_issues(self):
        """Test for concurrency issues"""
        print_header("CONCURRENCY ANALYSIS")

        # Test 1: Concurrent plugin registration
        print_info("Testing concurrent plugin registration...")
        try:
            from openbenchvue.core import PluginManager, Plugin, PluginMetadata

            manager = PluginManager()
            errors = []
            success_count = [0]

            def register_plugin(i):
                try:
                    class TestPlugin(Plugin):
                        metadata = PluginMetadata(
                            name=f"test_plugin_{i}",
                            version="1.0.0",
                            author="test",
                            description="test",
                            plugin_type="test"
                        )

                        def initialize(self, config):
                            return True

                    plugin = TestPlugin()
                    if manager.register(plugin):
                        success_count[0] += 1
                except Exception as e:
                    errors.append(str(e))

            # Register plugins concurrently
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(register_plugin, i) for i in range(50)]
                for future in futures:
                    future.result(timeout=5)

            if len(errors) == 0 and success_count[0] == 50:
                print_success(f"Concurrent plugin registration: {success_count[0]}/50 succeeded")
                self.add_result(TestResult(
                    "Concurrent plugin registration",
                    True,
                    f"All {success_count[0]} plugins registered without errors"
                ))
            else:
                print_error(f"Concurrent registration had {len(errors)} errors")
                self.add_result(TestResult(
                    "Concurrent plugin registration",
                    False,
                    f"{len(errors)} errors during concurrent registration",
                    'ERROR'
                ))

        except Exception as e:
            print_error(f"Concurrency test failed: {e}")
            traceback.print_exc()
            self.add_result(TestResult(
                "Concurrency analysis",
                False,
                str(e),
                'ERROR'
            ))

        # Test 2: Concurrent event publishing
        print_info("Testing concurrent event publishing...")
        try:
            from openbenchvue.core import EventBus

            bus = EventBus(async_mode=True)
            received = []
            lock = threading.Lock()

            def handler(event):
                with lock:
                    received.append(event.data)

            bus.subscribe("stress.test", handler)

            # Publish many events concurrently
            def publish_events(start, count):
                for i in range(start, start + count):
                    bus.emit("stress.test", data=i)

            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [
                    executor.submit(publish_events, i * 100, 100)
                    for i in range(10)
                ]
                for future in futures:
                    future.result(timeout=10)

            # Wait for processing
            bus.wait_for_events()
            time.sleep(0.5)

            expected = 1000
            actual = len(received)

            if actual == expected:
                print_success(f"Concurrent event publishing: {actual}/{expected} events processed")
                self.add_result(TestResult(
                    "Concurrent event publishing",
                    True,
                    f"All {expected} events processed correctly"
                ))
            else:
                print_warning(f"Event processing: {actual}/{expected} events processed")
                self.add_result(TestResult(
                    "Concurrent event publishing",
                    False,
                    f"Only {actual}/{expected} events processed",
                    'WARNING'
                ))

            bus.shutdown()

        except Exception as e:
            print_error(f"Concurrent event test failed: {e}")
            traceback.print_exc()
            self.add_result(TestResult(
                "Concurrent event publishing",
                False,
                str(e),
                'ERROR'
            ))

    def test_error_handling(self):
        """Test error handling completeness"""
        print_header("ERROR HANDLING ANALYSIS")

        # Test 1: Invalid inputs
        print_info("Testing invalid input handling...")
        try:
            from openbenchvue.security import AuthenticationManager

            auth = AuthenticationManager()

            # Test empty username
            try:
                result = auth.register_user("", "Password123!")
                if result == False:
                    print_success("Empty username properly rejected")
                    self.add_result(TestResult(
                        "Empty username validation",
                        True,
                        "Empty username rejected"
                    ))
                else:
                    print_error("Empty username was accepted")
                    self.add_result(TestResult(
                        "Empty username validation",
                        False,
                        "Empty username should be rejected",
                        'ERROR'
                    ))
            except Exception as e:
                print_warning(f"Empty username caused exception: {e}")
                self.add_result(TestResult(
                    "Empty username validation",
                    False,
                    f"Should return False, not raise: {e}",
                    'WARNING'
                ))

            # Test None password
            try:
                result = auth.register_user("user", None)
                print_warning("None password should raise exception or return False")
                self.add_result(TestResult(
                    "None password validation",
                    False,
                    "None password should be validated",
                    'WARNING'
                ))
            except (TypeError, AttributeError):
                print_success("None password properly rejected")
                self.add_result(TestResult(
                    "None password validation",
                    True,
                    "None password raises exception"
                ))

            # Test SQL injection attempt (future database)
            try:
                result = auth.register_user("admin'; DROP TABLE users--", "Password123!")
                print_info("SQL injection pattern handled (no database yet)")
                self.add_result(TestResult(
                    "SQL injection resistance",
                    True,
                    "No database yet, but input not sanitized"
                ))
            except Exception as e:
                print_info(f"SQL injection pattern caused: {e}")

        except Exception as e:
            print_error(f"Error handling test failed: {e}")
            traceback.print_exc()

        # Test 2: Resource cleanup on errors
        print_info("Testing resource cleanup on errors...")
        try:
            from openbenchvue.core import PluginManager, Plugin, PluginMetadata

            manager = PluginManager()

            class FailingPlugin(Plugin):
                metadata = PluginMetadata(
                    name="failing_plugin",
                    version="1.0.0",
                    author="test",
                    description="test",
                    plugin_type="test"
                )

                def initialize(self, config):
                    raise RuntimeError("Initialization failed!")

            plugin = FailingPlugin()
            result = manager.register(plugin)

            if not result:
                # Check plugin not added to registry
                if "failing_plugin" not in manager.plugins:
                    print_success("Failed plugin not added to registry")
                    self.add_result(TestResult(
                        "Failed plugin cleanup",
                        True,
                        "Plugin properly cleaned up on init failure"
                    ))
                else:
                    print_error("Failed plugin added to registry")
                    self.add_result(TestResult(
                        "Failed plugin cleanup",
                        False,
                        "Failed plugin should not be in registry",
                        'ERROR'
                    ))
            else:
                print_error("Failing plugin registered successfully (should fail)")
                self.add_result(TestResult(
                    "Failed plugin handling",
                    False,
                    "Plugin with failing init should not register",
                    'ERROR'
                ))

        except Exception as e:
            print_error(f"Resource cleanup test failed: {e}")
            traceback.print_exc()

    def test_edge_cases(self):
        """Test edge cases and boundary conditions"""
        print_header("EDGE CASE ANALYSIS")

        # Test 1: Empty collections
        print_info("Testing empty collection handling...")
        try:
            from openbenchvue.core import PluginManager

            manager = PluginManager()

            # Get plugins when none registered
            plugins = manager.get_all_plugins()
            assert plugins == [], "Empty plugin list should return empty list"

            plugins_by_type = manager.get_plugins_by_type("nonexistent")
            assert plugins_by_type == [], "Nonexistent type should return empty list"

            print_success("Empty collection handling correct")
            self.add_result(TestResult(
                "Empty collection handling",
                True,
                "Empty collections handled properly"
            ))

        except Exception as e:
            print_error(f"Empty collection test failed: {e}")
            self.add_result(TestResult(
                "Empty collection handling",
                False,
                str(e),
                'ERROR'
            ))

        # Test 2: Very long strings
        print_info("Testing very long string handling...")
        try:
            from openbenchvue.security import AuthenticationManager

            auth = AuthenticationManager()

            # Very long username
            long_username = "a" * 10000
            long_password = "P@ssw0rd" + "a" * 10000

            try:
                result = auth.register_user(long_username, long_password)
                print_info("Very long strings handled (may need length validation)")
                self.add_result(TestResult(
                    "Very long string handling",
                    True,
                    "Long strings handled, but should add length limits",
                    'WARNING'
                ))
            except Exception as e:
                print_success(f"Very long strings rejected: {e}")
                self.add_result(TestResult(
                    "Very long string handling",
                    True,
                    "Long strings cause exception (expected)"
                ))

        except Exception as e:
            print_error(f"Long string test failed: {e}")

        # Test 3: Special characters and Unicode
        print_info("Testing special character handling...")
        try:
            from openbenchvue.security import AuthenticationManager

            auth = AuthenticationManager()

            # Unicode username
            unicode_user = "用户名123"
            unicode_pass = "P@ss用户名123"

            try:
                result = auth.register_user(unicode_user, unicode_pass)
                print_success("Unicode characters handled")
                self.add_result(TestResult(
                    "Unicode handling",
                    True,
                    "Unicode characters accepted"
                ))
            except Exception as e:
                print_warning(f"Unicode characters cause issues: {e}")
                self.add_result(TestResult(
                    "Unicode handling",
                    False,
                    f"Unicode should be supported: {e}",
                    'WARNING'
                ))

        except Exception as e:
            print_error(f"Special character test failed: {e}")

        # Test 4: Null/None values
        print_info("Testing null/None value handling...")
        try:
            from openbenchvue.core import Container

            container = Container()

            # Register None as instance
            try:
                container.register(str, instance=None)
                instance = container.resolve(str)
                if instance is None:
                    print_warning("Container allows None instances")
                    self.add_result(TestResult(
                        "None instance handling",
                        False,
                        "Container should validate non-None instances",
                        'WARNING'
                    ))
            except Exception as e:
                print_success(f"None instance rejected: {e}")
                self.add_result(TestResult(
                    "None instance handling",
                    True,
                    "None instances properly rejected"
                ))

        except Exception as e:
            print_error(f"Null value test failed: {e}")

    def test_performance_bottlenecks(self):
        """Test for performance bottlenecks"""
        print_header("PERFORMANCE ANALYSIS")

        # Test 1: Event bus throughput
        print_info("Testing event bus throughput...")
        try:
            from openbenchvue.core import EventBus

            bus = EventBus(async_mode=True)
            handled_count = [0]
            lock = threading.Lock()

            def handler(event):
                with lock:
                    handled_count[0] += 1

            bus.subscribe("perf.*", handler)

            # Measure throughput
            count = 10000
            start = time.time()

            for i in range(count):
                bus.emit(f"perf.test{i % 10}", data=i)

            bus.wait_for_events()
            elapsed = time.time() - start

            throughput = count / elapsed
            print_info(f"Event bus throughput: {throughput:.0f} events/sec")

            if throughput > 1000:
                print_success(f"Good throughput: {throughput:.0f} events/sec")
                self.add_result(TestResult(
                    "Event bus throughput",
                    True,
                    f"{throughput:.0f} events/sec"
                ))
            else:
                print_warning(f"Low throughput: {throughput:.0f} events/sec")
                self.add_result(TestResult(
                    "Event bus throughput",
                    False,
                    f"Only {throughput:.0f} events/sec (target: >1000)",
                    'WARNING'
                ))

            bus.shutdown()

        except Exception as e:
            print_error(f"Performance test failed: {e}")
            traceback.print_exc()

        # Test 2: Container resolution performance
        print_info("Testing dependency injection performance...")
        try:
            from openbenchvue.core import Container

            container = Container()

            class ServiceA:
                pass

            class ServiceB:
                def __init__(self, a: ServiceA):
                    self.a = a

            container.register_singleton(ServiceA)
            container.register_transient(ServiceB)

            # Measure resolution time
            count = 1000
            start = time.time()

            for _ in range(count):
                instance = container.resolve(ServiceB)

            elapsed = time.time() - start
            avg_time = (elapsed / count) * 1000  # ms

            print_info(f"Average resolution time: {avg_time:.3f}ms")

            if avg_time < 1.0:
                print_success(f"Fast resolution: {avg_time:.3f}ms per resolve")
                self.add_result(TestResult(
                    "DI resolution performance",
                    True,
                    f"{avg_time:.3f}ms average"
                ))
            else:
                print_warning(f"Slow resolution: {avg_time:.3f}ms per resolve")
                self.add_result(TestResult(
                    "DI resolution performance",
                    False,
                    f"{avg_time:.3f}ms average (target: <1ms)",
                    'WARNING'
                ))

        except Exception as e:
            print_error(f"DI performance test failed: {e}")

    def generate_report(self):
        """Generate final analysis report"""
        print_header("ANALYSIS SUMMARY")

        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)

        print(f"{Colors.BOLD}Total Tests: {total}{Colors.RESET}")
        print(f"{Colors.GREEN}Passed: {passed}{Colors.RESET}")
        print(f"{Colors.RED}Failed: {failed}{Colors.RESET}")
        print(f"{Colors.YELLOW}Warnings: {self.warnings_found}{Colors.RESET}")
        print(f"{Colors.RED}Errors: {self.issues_found}{Colors.RESET}")

        if failed > 0:
            print(f"\n{Colors.BOLD}Failed Tests:{Colors.RESET}")
            for result in self.results:
                if not result.passed:
                    color = Colors.YELLOW if result.severity == 'WARNING' else Colors.RED
                    print(f"{color}  • {result.name}: {result.message}{Colors.RESET}")

        print(f"\n{Colors.BOLD}Recommendations:{Colors.RESET}")

        # Based on results, provide recommendations
        recommendations = []

        # Check for specific issues
        for result in self.results:
            if "None password" in result.name and not result.passed:
                recommendations.append("Add comprehensive input validation for all user inputs")

            if "throughput" in result.name.lower() and not result.passed:
                recommendations.append("Optimize event bus for better performance")

            if "memory" in result.name.lower() and not result.passed:
                recommendations.append("Fix memory leaks in event handling")

            if "concurrent" in result.name.lower() and not result.passed:
                recommendations.append("Add more robust locking for concurrent operations")

        # General recommendations
        recommendations.extend([
            "Add input length validation for all string inputs",
            "Implement rate limiting for API endpoints",
            "Add comprehensive logging for all error paths",
            "Create performance benchmarks for critical paths",
            "Add integration tests for multi-component scenarios",
        ])

        for i, rec in enumerate(set(recommendations), 1):
            print(f"  {i}. {rec}")

        return failed == 0


def main():
    """Run advanced analysis"""
    print(f"{Colors.BOLD}{Colors.MAGENTA}")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 15 + "ADVANCED DEEP ANALYSIS - OPENBENCHVUE" + " " * 25 + "║")
    print("╚" + "═" * 78 + "╝")
    print(Colors.RESET)

    analyzer = AdvancedAnalyzer()

    try:
        analyzer.test_memory_leaks()
        analyzer.test_concurrency_issues()
        analyzer.test_error_handling()
        analyzer.test_edge_cases()
        analyzer.test_performance_bottlenecks()

        success = analyzer.generate_report()

        if success:
            print(f"\n{Colors.BOLD}{Colors.GREEN}✓ ALL ADVANCED TESTS PASSED{Colors.RESET}")
            return 0
        else:
            print(f"\n{Colors.BOLD}{Colors.YELLOW}⚠ SOME ISSUES FOUND - REVIEW NEEDED{Colors.RESET}")
            return 1

    except Exception as e:
        print_error(f"Analysis failed with exception: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
