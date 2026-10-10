#!/usr/bin/env python3
"""
Simple test endpoint for Vercel deployment
"""

def handler(request):
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": {
            "message": "🦆 Duck Store API is working!",
            "status": "success",
            "timestamp": "2025-08-25"
        }
    }
