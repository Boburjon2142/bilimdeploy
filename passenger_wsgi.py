import os
import sys

project_path = "/home/bilimsto/bilim_project"
if project_path not in sys.path:
    sys.path.append(project_path)

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings"
)

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
