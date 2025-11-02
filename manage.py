import argparse
from core.orchestrator import Orchestrator

def main():
    parser = argparse.ArgumentParser(description="System management interface")
    parser.add_argument("--status", action="store_true", help="Show system status")
    parser.add_argument("--start", action="store_true", help="Start orchestrator")
    parser.add_argument("--reboot", action="store_true", help="Restart modules")
    args = parser.parse_args()

    orchestrator = Orchestrator()

    if args.start:
        orchestrator.start()
    elif args.status:
        orchestrator.status()
    elif args.reboot:
        print("[System] Rebooting modules...")
        orchestrator.start()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
