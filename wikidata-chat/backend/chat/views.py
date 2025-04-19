# backend/chat/views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Chat, Message
from .serializers import ChatSerializer, ChatListSerializer, MessageSerializer

class ChatViewSet(viewsets.ViewSet):
    def list(self, request):
        """Get all chats"""
        chats = Chat.objects.all()
        serializer = ChatListSerializer(chats, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        """Get a single chat with its messages"""
        try:
            chat = Chat.objects.get(pk=pk)
            serializer = ChatSerializer(chat)
            return Response(serializer.data)
        except Chat.DoesNotExist:
            return Response({"error": "Chat not found"}, status=status.HTTP_404_NOT_FOUND)
    
    def create(self, request):
        """Create a new chat"""
        chat = Chat.objects.create()
        serializer = ChatListSerializer(chat)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def destroy(self, request, pk=None):
        """Delete a chat"""
        try:
            chat = Chat.objects.get(pk=pk)
            chat.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Chat.DoesNotExist:
            return Response({"error": "Chat not found"}, status=status.HTTP_404_NOT_FOUND)
