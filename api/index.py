"""Vercel serverless function entry point for BuddyAI Flask app"""
import sys
import os

# Add parent directory to path to import app module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

# Export the app for Vercel
__all__ = ['app']
