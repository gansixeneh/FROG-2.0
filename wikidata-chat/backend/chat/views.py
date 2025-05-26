# backend/chat/views.py
import json
import traceback
import logging
import os
from django.http import HttpResponse, Http404
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
                response, visualization_files_paths = agent.query(message_content, settings_data)
                
                # Save assistant message
                assistant_message = self.save_message(chat, response, 'assistant')
                
                # Create visualization file URLs if files exist
                visualization_files = None
                if visualization_files_paths:
                    from django.urls import reverse
                    visualization_files = {}
                    for file_type, file_path in visualization_files_paths.items():
                        if file_path and os.path.exists(file_path):
                            # Create download URL for each file type
                            download_url = f"/api/chats/{pk}/download_visualization/?type={file_type}"
                            visualization_files[file_type] = {
                                'download_url': download_url,
                                'file_name': os.path.basename(file_path)
                            }
                
                # Send response via Pusher
                pusher_service.send_chat_message(
                    pk, 
                    'assistant', 
                    response, 
                    str(assistant_message.id),
                    visualization_files
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
    
    @action(detail=True, methods=['get'])
    def download_visualization(self, request, pk=None):
        """Download visualization files"""
        try:
            chat = Chat.objects.get(pk=pk)
        except Chat.DoesNotExist:
            return Response({"error": "Chat not found"}, status=status.HTTP_404_NOT_FOUND)
        
        file_type = request.GET.get('type')
        if not file_type or file_type not in ['json', 'mermaid', 'ttl']:
            return Response({"error": "Invalid file type"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get agent instance to access visualization files
        gemini_api_key = os.environ.get('GEMINI_API_KEY')
        agent = get_agent(api_key=gemini_api_key)
        
        if not hasattr(agent, 'visualization_files') or not agent.visualization_files:
            return Response({"error": "No visualization files available"}, status=status.HTTP_404_NOT_FOUND)
        
        file_path = agent.visualization_files.get(file_type)
        if not file_path or not os.path.exists(file_path):
            return Response({"error": f"File of type {file_type} not found"}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            # Set appropriate content type
            content_types = {
                'json': 'application/json',
                'mermaid': 'text/plain',
                'ttl': 'text/turtle'
            }
            
            # Set appropriate file extension
            extensions = {
                'json': 'json',
                'mermaid': 'mmd',
                'ttl': 'ttl'
            }
            
            response = HttpResponse(file_content, content_type=content_types.get(file_type, 'text/plain'))
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
            return response
            
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return Response({"error": f"Error reading file: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
