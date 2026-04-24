"""
WSGI config for CareerAI project.
==================================
Exposes the WSGI callable as a module-level variable named ``application``.
"""
from dotenv import load_dotenv
load_dotenv()
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

application = get_wsgi_application()
