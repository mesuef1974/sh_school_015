"""
ASGI config for core project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import asyncio
import os
import sys

# On Windows, prefer SelectorEventLoop to avoid noisy Proactor transport errors
# like WinError 10054 during client disconnects when running under Uvicorn.
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        # If policy is not available or fails, continue with defaults
        pass

from django.conf import settings
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

application = get_asgi_application()

# In development, wrap with ASGI static files handler to serve static assets
# without triggering StreamingHttpResponse warnings under ASGI servers.
if settings.DEBUG:
    application = ASGIStaticFilesHandler(application)
