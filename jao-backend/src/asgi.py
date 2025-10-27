"""
ASGI config for job_advert_optimiser project.
It exposes the ASGI callable as a module-level variable named ``application``.
For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""
from jao_backend.api.consumers import JobAdvertConsumer
import os
import dotenv
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import path

dotenv.load_dotenv()
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jao_backend.settings.dev")

django_asgi_app = get_asgi_application()


application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": URLRouter([
        path("ws/job_advert/", JobAdvertConsumer.as_asgi()),
    ]),
})
