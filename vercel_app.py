"""
Vercel entry point.

This used to be a second, trimmed-down copy of the store that had drifted out of sync
(it had no cart or checkout routes, while its templates linked to them). It now serves
the one real app from duck_store.py; Vercel-specific settings (uploads in /tmp, secure
cookies) are applied there when the VERCEL environment variable is present.
"""

from duck_store import app  # noqa: F401  (re-exported for api/index.py)
