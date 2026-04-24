"""
ASGI config for CareerAI project.
==================================
Configures standard ASGI application for deployment with uvicorn/gunicorn.
"""
from dotenv import load_dotenv
load_dotenv()
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

application = get_asgi_application()
