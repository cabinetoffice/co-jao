"""
ASGI config for job_advert_optimiser project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

from jao_web.job_advert_optimiser.consumers import JobAdvertConsumer
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jao_backend.settings.base')

# Initialize Django ASGI application early
django_asgi_app = get_asgi_application()

# Import after get_asgi_application() to avoid AppRegistryNotReady

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter([
            path('ws/job_advert/', JobAdvertConsumer.as_asgi()),
        ])
    ),
})
