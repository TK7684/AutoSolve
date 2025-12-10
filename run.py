#!/usr/bin/env python3
"""
Run script for AutoSolve application.
This is the main entry point for users.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set working directory
os.chdir(Path(__file__).parent)

# Import and run the main application
from main import main

if __name__ == "__main__":
    print("Starting AutoSolve...")
    main()