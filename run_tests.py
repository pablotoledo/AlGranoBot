#!/usr/bin/env python3
"""
Test runner script for AlGranoBot.
Provides easy access to run different test suites.
"""

import sys
import subprocess
import argparse


def run_command(cmd):
    """Run a command and return success status."""
    try:
        result = subprocess.run(cmd, shell=True, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}")
        return False


def main():
    parser = argparse.ArgumentParser(description="AlGranoBot Test Runner")
    parser.add_argument(
        "test_type",
        choices=["all", "m4a", "audio", "quick", "verbose"],
        nargs="?",
        default="all",
        help="Type of tests to run"
    )
    
    args = parser.parse_args()
    
    commands = {
        "all": "pytest",
        "m4a": "pytest test_m4a_support.py",
        "audio": "pytest test_audio_formats.py", 
        "quick": "pytest -x",  # Stop at first failure
        "verbose": "pytest -v --tb=long"
    }
    
    cmd = commands.get(args.test_type, "pytest")
    
    print(f"🧪 Running: {cmd}")
    print("=" * 50)
    
    success = run_command(cmd)
    
    if success:
        print("\n🎉 All tests passed!")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
