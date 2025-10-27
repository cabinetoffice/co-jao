"""
ASGI config for frontend project.
"""
import os
import dotenv
from django.core.asgi import get_asgi_application

dotenv.load_dotenv()
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jao_web.settings.dev")

application = get_asgi_application()
