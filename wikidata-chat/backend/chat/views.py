# backend/chat/views.py
import json
import traceback
import logging
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Chat, Message
from .serializers import ChatSerializer, ChatListSerializer, MessageSerializer
from .pusher_service import pusher_service
from agent.singletons import get_agent
import asyncio
import os
import uuid
import time
import threading

# Configure logging
logger = logging.getLogger(__name__)

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
    
    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Send a message to a chat via HTTP API"""
        try:
            chat = Chat.objects.get(pk=pk)
        except Chat.DoesNotExist:
            return Response({"error": "Chat not found"}, status=status.HTTP_404_NOT_FOUND)
        
        message_content = request.data.get('message', '')
        settings_data = request.data.get('settings', {})
        
        if not message_content.strip():
            return Response({"error": "Message cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Send "thinking" message
        pusher_service.send_system_message(pk, '🧠 Agent is thinking...')
        
        # Save user message
        user_message = self.save_message(chat, message_content, 'user')
        
        # Process the message asynchronously
        def process_message():
            try:
                # Get agent with debug callback
                gemini_api_key = os.environ.get('GEMINI_API_KEY')
                
                def debug_callback(output):
                    # Fun emojis for each node type
                    node_emojis = {
                        "Translation Node": "🌍",
                        "Entity Extraction Node": "🕵️",
                        "Strategy Selection Node": "🔀",
                        "Verbalization Node": "🗣️", 
                        "Property Generation Node": "🧩",
                        "SPARQL Generation Node": "⚙️",
                        "Answer Generation Node": "🎁",
                        "Google Search Node": "🔍",
                        "default": "🐸"
                    }
                    
                    # Extract the node name from the output if possible
                    node_name = None
                    for key in node_emojis:
                        if key in output:
                            node_name = key
                            break
                    
                    # Use the appropriate emoji
                    emoji = node_emojis.get(node_name, node_emojis["default"])
                    
                    # Format the message with the emoji
                    decorated_output = f"{emoji} {output}"
                    
                    # Send via Pusher
                    pusher_service.send_debug_message(pk, decorated_output)
                
                agent = get_agent(api_key=gemini_api_key, debug_callback=debug_callback)
                
                # Process the message
                response, visualization_files_content = agent.query(message_content, settings_data)
                
                # Save assistant message
                assistant_message = self.save_message(chat, response, 'assistant')
                
                # Send response via Pusher
                pusher_service.send_chat_message(
                    pk, 
                    'assistant', 
                    response, 
                    str(assistant_message.id),
                    visualization_files_content
                )
                
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                error_message = f"Error: {str(e)}\n{traceback.format_exc()}"
                error_msg_obj = self.save_message(chat, error_message, 'system')
                
                pusher_service.send_system_message(pk, error_message)
        
        # Run processing in a separate thread
        thread = threading.Thread(target=process_message)
        thread.daemon = True
        thread.start()
        
        return Response({"status": "processing"}, status=status.HTTP_202_ACCEPTED)
    
    def save_message(self, chat, content, role):
        """Save a message to the database"""
        # Update chat title based on first user message if it's a new chat
        if role == 'user' and chat.title == "New Chat":
            # Truncate long messages for the title
            chat.title = content[:50] + ("..." if len(content) > 50 else "")
            chat.save()
        
        return Message.objects.create(
            chat=chat,
            role=role,
            content=content
        )
