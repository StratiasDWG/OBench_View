"""
OpenBenchVue Main Entry Point

Command-line interface and application launcher.
"""

import sys
import logging
import argparse
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('openbenchvue.log')
    ]
)

logger = logging.getLogger(__name__)


def setup_logging(level: str):
    """Configure logging level"""
    numeric_level = getattr(logging, level.upper(), None)
    if isinstance(numeric_level, int):
        logging.getLogger().setLevel(numeric_level)


def launch_gui(config_file: str = None):
    """Launch GUI application"""
    try:
        from .gui.main_window import MainWindow
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import Qt

        logger.info("Starting OpenBenchVue GUI...")

        # Enable high DPI scaling
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        app = QApplication(sys.argv)
        app.setApplicationName("OpenBenchVue")
        app.setOrganizationName("OpenBenchVue")

        # Create main window
        window = MainWindow(config_file=config_file)
        window.show()

        logger.info("GUI launched successfully")
        sys.exit(app.exec_())

    except ImportError as e:
        logger.error(f"GUI dependencies not available: {e}")
        logger.error("Please install PyQt5: pip install PyQt5")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to launch GUI: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def run_cli_mode(args):
    """Run in command-line interface mode"""
    from .instruments.detector import InstrumentDetector
    from . import config

    logger.info("Running in CLI mode...")

    # Initialize detector
    detector = InstrumentDetector(visa_backend=config.get('visa.backend', '@iolib'))

    if args.scan:
        # Scan for instruments
        logger.info("Scanning for instruments...")
        identities = detector.detect_instruments()

        if identities:
            print(f"\nFound {len(identities)} instrument(s):\n")
            for i, ident in enumerate(identities, 1):
                print(f"{i}. {ident.manufacturer} {ident.model}")
                print(f"   Type: {ident.instrument_type.value}")
                print(f"   Resource: {ident.resource_string}")
                print(f"   Serial: {ident.serial_number}\n")
        else:
            print("No instruments detected.")

    elif args.connect:
        # Connect to specific instrument
        logger.info(f"Connecting to {args.connect}...")

        identity = detector.identify_instrument(args.connect)
        if identity:
            print(f"Identified: {identity.manufacturer} {identity.model}")

            instrument = detector.create_instrument(identity)
            if instrument:
                instrument.connect()
                print(f"Connected successfully!")

                # Get capabilities
                caps = instrument.get_capabilities()
                print(f"\nCapabilities: {caps}")

                # Get status
                status = instrument.get_status()
                print(f"\nStatus: {status}")

                instrument.disconnect()
        else:
            print(f"Could not identify instrument at {args.connect}")

    elif args.sequence:
        # Run sequence
        from .automation.sequence import SequenceLoader
        from .automation.executor import SequenceExecutor, ExecutionContext

        logger.info(f"Loading sequence: {args.sequence}")

        try:
            sequence = SequenceLoader.load(args.sequence)
            print(f"\nLoaded sequence: {sequence.name}")
            print(f"Description: {sequence.description}")
            print(f"Blocks: {len(sequence.blocks)}\n")

            # Auto-connect to instruments
            print("Connecting to instruments...")
            instruments = detector.auto_connect()

            if not instruments:
                print("No instruments connected. Cannot run sequence.")
                return

            print(f"Connected to {len(instruments)} instrument(s)\n")

            # Create execution context
            context = ExecutionContext(instruments=instruments)

            # Create executor
            executor = SequenceExecutor(sequence, context)

            # Register progress callback
            def progress_callback(block, index, result, state):
                print(f"[{index+1}/{len(sequence)}] {block.name}: {result.get('status', 'unknown')}")

            executor.register_progress_callback(progress_callback)

            # Execute
            print("Executing sequence...\n")
            result = executor.start()

            # Print results
            print(f"\nExecution {result.state.value}")
            print(f"Blocks executed: {result.blocks_executed}")
            print(f"Duration: {result.duration:.2f}s")

            if result.errors:
                print(f"\nErrors:")
                for error in result.errors:
                    print(f"  - {error}")

            if result.variables:
                print(f"\nVariables:")
                for name, value in result.variables.items():
                    print(f"  {name} = {value}")

            # Disconnect
            for instrument in instruments.values():
                instrument.disconnect()

        except Exception as e:
            logger.error(f"Sequence execution failed: {e}")
            import traceback
            traceback.print_exc()

    elif args.remote:
        # Start remote server
        from .remote.server import RemoteServer

        logger.info("Starting remote server...")

        # Auto-connect to instruments
        detector = InstrumentDetector()
        instruments = detector.auto_connect()

        # Create server
        server = RemoteServer(host='0.0.0.0', port=args.port)
        server.set_instruments(instruments)

        print(f"\n✓ Remote server started")
        print(f"  Access dashboard at: {server.get_url()}")
        print(f"  Connected instruments: {len(instruments)}")
        print("\nPress Ctrl+C to stop...\n")

        server.start()

        # Keep running
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            server.stop()

    else:
        print("No action specified. Use --help for usage information.")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='OpenBenchVue - Open-source instrument control and test automation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  openbenchvue                          # Launch GUI
  openbenchvue --scan                   # Scan for instruments
  openbenchvue --connect USB0::0x1234   # Connect to specific instrument
  openbenchvue --sequence test.yaml     # Run test sequence
  openbenchvue --remote                 # Start remote web server
        """
    )

    parser.add_argument(
        '--gui',
        action='store_true',
        help='Launch GUI (default if no other options specified)'
    )

    parser.add_argument(
        '--scan',
        action='store_true',
        help='Scan for connected instruments'
    )

    parser.add_argument(
        '--connect',
        metavar='RESOURCE',
        help='Connect to specific instrument resource'
    )

    parser.add_argument(
        '--sequence',
        metavar='FILE',
        help='Execute test sequence from file'
    )

    parser.add_argument(
        '--remote',
        action='store_true',
        help='Start remote web server'
    )

    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='Port for remote server (default: 5000)'
    )

    parser.add_argument(
        '--config',
        metavar='FILE',
        help='Configuration file path'
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='OpenBenchVue 0.1.0'
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)

    # Load config if specified
    if args.config:
        from . import config
        config.load(args.config)

    # Determine mode
    if args.scan or args.connect or args.sequence or args.remote:
        # CLI mode
        run_cli_mode(args)
    else:
        # GUI mode (default)
        launch_gui(config_file=args.config)


if __name__ == '__main__':
    main()
