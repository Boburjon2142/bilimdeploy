import os

# Use production settings by default; only fall back to dev when explicitly enabled.
if os.environ.get("DJANGO_DEBUG", "False").lower() == "true":
    from backend.settings.dev import *  # noqa
else:
    from backend.settings.prod import *  # noqa
