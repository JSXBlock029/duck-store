#!/usr/bin/env python3
"""
Vercel API entry point for Duck Store
This file is required for Vercel to properly serve the Flask application
"""

import sys
import os

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Flask app from vercel_app.py
from vercel_app import app

# Export the app for Vercel
handler = app
