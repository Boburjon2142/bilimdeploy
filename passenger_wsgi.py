import os
import sys

# Resolve project root relative to this file to work on shared hosting paths.
PROJECT_HOME = os.path.dirname(os.path.abspath(__file__))
if PROJECT_HOME not in sys.path:
    sys.path.insert(0, PROJECT_HOME)

# Default to production settings; override via env if needed.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings.prod")

from django.core.wsgi import get_wsgi_application  # noqa
application = get_wsgi_application()
