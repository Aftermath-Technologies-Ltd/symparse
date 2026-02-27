import argparse
import sys
import json
import logging

def parse_args():
    parser = argparse.ArgumentParser(description="Symparse: LLM to Fast-Path Regex Compiler pipeline")
    
    try:
        from importlib.metadata import version
        v = version("symparse")
    except Exception:
        v = "unknown"
        
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("--version", action="version", version=f"%(prog)s {v}")
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # "run" command
    run_parser = subparsers.add_parser("run", help="Run the pipeline parser")
    run_parser.add_argument("--stats", action="store_true", help="Print performance cache stats when finished")
    run_parser.add_argument("--schema", required=True, help="Path to JSON schema file")
    run_parser.add_argument("--compile", action="store_true", help="Compile a fast-path script on success")
    run_parser.add_argument("--force-ai", action="store_true", help="Bypass local cache and force AI execution")
    run_parser.add_argument("--confidence", type=float, default=None, help="Token logprob threshold (default: -2.0)")
    run_parser.add_argument("--model", type=str, help="Override AI backend model (e.g. ollama/gemma3:1b, openai/gpt-4o)")
    run_parser.add_argument("--embed", action="store_true", help="Use local embeddings for tier-2 caching (requires sentence-transformers)")

    # "cache" command
    cache_parser = subparsers.add_parser("cache", help="Manage the local cache")
    cache_subparsers = cache_parser.add_subparsers(dest="cache_command", required=True)
    cache_subparsers.add_parser("list", help="Display cached extraction scripts")
    cache_subparsers.add_parser("clear", help="Wipe the local compilation directory")
    
    return parser.parse_args()

def main():
    args = parse_args()
    
    log_level = logging.DEBUG if getattr(args, "verbose", False) else logging.ERROR
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
            
        import os
        from symparse.engine import process_stream, EngineFailure, GracefulDegradationMode, global_stats
        
        try:
            with open(args.schema, 'r') as f:
                schema_dict = json.load(f)
        except Exception as e:
            print(f"Error reading schema file: {e}", file=sys.stderr)
            sys.exit(1)
            
        degradation_mode = os.getenv("SYMPARSE_DEGRADATION_MODE", "halt").lower()
        mode = GracefulDegradationMode.PASSTHROUGH if degradation_mode == "passthrough" else GracefulDegradationMode.HALT
            
        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                result = process_stream(
                    line, 
                    schema_dict, 
                    compile=args.compile,
                    force_ai=args.force_ai,
                    degradation_mode=mode,
                    confidence_threshold=getattr(args, "confidence", None),
                    use_embeddings=getattr(args, "embed", False),
                    model=getattr(args, "model", None)
                )
                print(json.dumps(result))
                sys.stdout.flush()
        except EngineFailure as e:
            print(f"Engine Failure: {e}", file=sys.stderr)
            sys.exit(1)
        except KeyboardInterrupt:
            pass
            
        if getattr(args, "stats", False):
            total_runs = global_stats.fast_path_hits + global_stats.ai_path_hits
            avg_latency = global_stats.total_latency_ms / total_runs if total_runs > 0 else 0.0
            
            try:
                from importlib.metadata import version
                v = version("symparse")
            except Exception:
                v = "unknown"
                
            print(f"\n--- Symparse Run Stats (v{v}) ---", file=sys.stderr)
            print(f"Fast Path Hits: {global_stats.fast_path_hits}", file=sys.stderr)
            print(f"AI Path Hits:   {global_stats.ai_path_hits}", file=sys.stderr)
            print(f"Average Latency: {avg_latency:.2f}ms", file=sys.stderr)
        
if __name__ == "__main__":
    main()
