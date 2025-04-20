# backend/wikidata_web/asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Set the Django settings module before importing chat.routing
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wikidata_web.settings')

# Import Django ASGI application first
django_asgi_app = get_asgi_application()

# Import chat.routing after Django has been set up
import chat.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            chat.routing.websocket_urlpatterns
        )
    ),
})