"""
Rate limiter dependency — centralized to avoid circular imports.

Imported by main.py (to attach to app.state) and by routers (to apply limits).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
