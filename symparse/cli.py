import argparse
import sys
import json

def parse_args():
    parser = argparse.ArgumentParser(
        description="Self-optimizing Unix pipeline tool with neurosymbolic parsing."
    )
    
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # "run" command
    run_parser = subparsers.add_parser("run", help="Run the pipeline parser")
    run_parser.add_argument("--schema", required=True, help="Path to JSON schema file")
    run_parser.add_argument("--compile", action="store_true", help="Compile a fast-path script on success")
    run_parser.add_argument("--force-ai", action="store_true", help="Bypass local cache and force AI execution")
    run_parser.add_argument("--confidence", type=float, help="Override average logprob confidence threshold (e.g. -2.0)")

    # "cache" command
    cache_parser = subparsers.add_parser("cache", help="Manage the local cache")
    cache_subparsers = cache_parser.add_subparsers(dest="cache_command", required=True)
    cache_subparsers.add_parser("list", help="Display cached extraction scripts")
    cache_subparsers.add_parser("clear", help="Wipe the local compilation directory")
    
    return parser.parse_args()

def main():
    args = parse_args()
    
    import logging
    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")
    
    if args.command == "cache":
        from symparse.cache_manager import CacheManager
        manager = CacheManager()
        if args.cache_command == "list":
            print(json.dumps(manager.list_cache(), indent=2))
        elif args.cache_command == "clear":
            manager.clear_cache()
            print("Cache cleared.")
        sys.exit(0)
        
    if args.command == "run":
        if sys.stdin.isatty():
            print("Error: No data piped into stdin.", file=sys.stderr)
            sys.exit(1)
            
        input_data = sys.stdin.read()
        if not input_data.strip():
             print("Error: Empty stdin stream.", file=sys.stderr)
             sys.exit(1)
             
        import os
        from symparse.engine import process_stream, EngineFailure, GracefulDegradationMode
        
        try:
            with open(args.schema, 'r') as f:
                schema_dict = json.load(f)
        except Exception as e:
            print(f"Error reading schema file: {e}", file=sys.stderr)
            sys.exit(1)
            
        degradation_mode = os.getenv("SYMPARSE_DEGRADATION_MODE", "halt").lower()
        mode = GracefulDegradationMode.PASSTHROUGH if degradation_mode == "passthrough" else GracefulDegradationMode.HALT
            
        try:
            result = process_stream(
                input_data, 
                schema_dict, 
                compile=args.compile,
                force_ai=args.force_ai,
                degradation_mode=mode,
                confidence_threshold=getattr(args, "confidence", None)
            )
            print(json.dumps(result, indent=2))
        except EngineFailure as e:
            print(f"Engine Failure: {e}", file=sys.stderr)
            sys.exit(1)
        
if __name__ == "__main__":
    main()
