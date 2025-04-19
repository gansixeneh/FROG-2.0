# backend/chat/urls.py
from django.urls import path
from .views import ChatViewSet

urlpatterns = [
    path('chats/', ChatViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('chats/<uuid:pk>/', ChatViewSet.as_view({'get': 'retrieve', 'delete': 'destroy'})),
]