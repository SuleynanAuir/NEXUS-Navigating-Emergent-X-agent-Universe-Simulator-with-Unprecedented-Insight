#!/usr/bin/env python3
"""
MARDS v2 Command Line Interface

Usage:
    python main.py --deepseek_key YOUR_KEY --tavily_key YOUR_KEY --query "Your research question"
"""

import asyncio
import sys
import argparse
import logging
from pathlib import Path
import os

# Set up path
os.chdir(Path(__file__).parent)
sys.path.insert(0, str(Path(__file__).parent.parent))

# Now import from the module
if __name__ == "__main__":
    # Import after path setup - use fast controller for speed
    from v2_paragraph_reflective.controller_fast import MARDSControllerFast as MARDSController

    def setup_logging(log_level=logging.INFO):
        """Setup logging configuration."""
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler("mards.log")
            ]
        )

    def main():
        """Main CLI entry point."""
        parser = argparse.ArgumentParser(
            description="MARDS v2: Paragraph-level Iterative Reflective Deep Search Framework",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  python main.py --deepseek_key sk-xxx --tavily_key tvly-xxx --query "什么是量子计算"
  python main.py --deepseek_key sk-xxx --tavily_key tvly-xxx --query "气候变化的影响" --max_reflection_loops 5
            """
        )
        
        # Required arguments
        parser.add_argument(
            "--deepseek_key",
            required=True,
            help="DeepSeek API key (or set DEEPSEEK_API_KEY environment variable)"
        )
        parser.add_argument(
            "--tavily_key",
            required=True,
            help="Tavily API key (or set TAVILY_API_KEY environment variable)"
        )
        parser.add_argument(
            "--query",
            required=True,
            help="Research query to process"
        )
        
        # Optional arguments
        parser.add_argument(
            "--results_dir",
            default="runs",
            help="Directory to save results (default: runs)"
        )
        parser.add_argument(
            "--max_reflection_loops",
            type=int,
            default=3,
            help="Maximum reflection loops per section (default: 3)"
        )
        parser.add_argument(
            "--force_reflection",
            type=int,
            choices=[0, 1],
            default=0,
            help="Force reflection mode for each section: 1=enable, 0=disable (default: 0)"
        )
        parser.add_argument(
            "--min_reflection_loops",
            type=int,
            default=0,
            help="Minimum reflection loops per section when force reflection is enabled (default: 0)"
        )
        parser.add_argument(
            "--reflection_sensitivity",
            type=float,
            default=1.0,
            help="Reflection gain sensitivity in [0.5, 2.0], higher means more aggressive confidence lift (default: 1.0)"
        )
        parser.add_argument(
            "--uncertainty_threshold",
            type=float,
            default=0.2,
            help="Uncertainty threshold for proceeding (default: 0.2)"
        )
        parser.add_argument(
            "--log_level",
            default="INFO",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            help="Logging level (default: INFO)"
        )
        parser.add_argument(
            "--deterministic",
            action="store_true",
            help="Enable deterministic mode (reproducible results)"
        )
        
        args = parser.parse_args()
        
        # Setup logging
        log_level = getattr(logging, args.log_level)
        setup_logging(log_level)
        
        logger = logging.getLogger(__name__)

        if args.max_reflection_loops < 0:
            parser.error("--max_reflection_loops must be >= 0")
        if args.min_reflection_loops < 0:
            parser.error("--min_reflection_loops must be >= 0")
        if args.min_reflection_loops > args.max_reflection_loops:
            parser.error("--min_reflection_loops cannot exceed --max_reflection_loops")
        if not (0.5 <= args.reflection_sensitivity <= 2.0):
            parser.error("--reflection_sensitivity must be within [0.5, 2.0]")
        
        try:
            # Create controller
            controller = MARDSController(
                deepseek_key=args.deepseek_key,
                tavily_key=args.tavily_key,
                results_dir=args.results_dir,
                max_reflection_loops=args.max_reflection_loops,
                force_reflection=bool(args.force_reflection),
                min_reflection_loops=args.min_reflection_loops,
                reflection_sensitivity=args.reflection_sensitivity,
                uncertainty_threshold=args.uncertainty_threshold,
                deterministic=args.deterministic
            )
            
            # Run workflow
            result = asyncio.run(controller.run(
                query=args.query,
                enable_reflection=True
            ))
            
            # Display results
            print("\n" + "="*80)
            print("MARDS v2 Fast Mode - WORKFLOW COMPLETED")
            print("="*80)
            print(f"\nQuery: {result['query']}")
            print(f"Title: {result['title']}")
            print(f"Global Uncertainty: {result['global_uncertainty']:.2%}")
            print(f"Sections: {result['sections_count']}")
            print(f"Status: {result['status']}")
            print(f"\nTask ID: {result['task_id']}")
            print(f"Timestamp: {result['timestamp']}")
            print(f"\nReport Preview:")
            print("-"*80)
            report_lines = result['report_markdown'].split('\n')
            # Print first 50 lines
            for line in report_lines[:50]:
                print(line)
            if len(report_lines) > 50:
                print(f"\n... ({len(report_lines) - 50} more lines)")
            print("\n" + "="*80)
            print(f"Full report saved to: runs/{result['task_id']}_final.json")
            
            return 0
        
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            return 130
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            print(f"\nError: {e}")
            return 1

    sys.exit(main())
