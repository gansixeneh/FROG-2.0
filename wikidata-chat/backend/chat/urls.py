# backend/chat/urls.py
from django.urls import path
from .views import ChatViewSet

urlpatterns = [
    path('chats/', ChatViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('chats/<uuid:pk>/', ChatViewSet.as_view({'get': 'retrieve', 'delete': 'destroy'})),
    path('chats/<uuid:pk>/send_message/', ChatViewSet.as_view({'post': 'send_message'})),
]
