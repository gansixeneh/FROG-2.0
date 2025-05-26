# backend/chat/consumers.py
import json
import traceback
import logging
import os
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Chat, Message
import asyncio
import uuid
import time

# Import the agent singleton instead of the WikidataAgent directly
from agent.singletons import get_agent

# Configure logging
logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.room_group_name = f'chat_{self.chat_id}'
        
        # Check if chat exists before proceeding
        chat_exists = await self.chat_exists(self.chat_id)
        if not chat_exists:
            # If chat doesn't exist, create it automatically
            await self.create_chat(self.chat_id)
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Get API key from environment
        gemini_api_key = os.environ.get('GEMINI_API_KEY')
        
        # Use the agent singleton instead of creating a new instance
        self.agent = get_agent(api_key=gemini_api_key, debug_callback=self.debug_callback)
        logger.info(f"Connected WebSocket for chat_id: {self.chat_id}, using shared agent instance")
        
        # Add a message counter to prevent duplicate message issues
        self.message_counter = 0
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        logger.info(f"Disconnected WebSocket for chat_id: {self.chat_id}")
    
    @database_sync_to_async
    def chat_exists(self, chat_id):
        """Check if a chat with the given ID exists"""
        try:
            return Chat.objects.filter(id=chat_id).exists()
        except Exception as e:
            logger.error(f"Error checking if chat exists: {e}")
            return False
    
    @database_sync_to_async
    def create_chat(self, chat_id):
        """Create a new chat with the specified ID"""
        try:
            # Try to convert the chat_id string to a UUID object
            chat_uuid = uuid.UUID(chat_id)
            return Chat.objects.create(id=chat_uuid, title="New Chat")
        except Exception as e:
            logger.error(f"Error creating chat: {e}")
            return None    
    # backend/chat/consumers.py - Updated debug_callback method

    async def debug_callback(self, output):
        """Callback function for agent debugging output with real-time streaming"""
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
            # Default emoji for any unrecognized nodes
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
        
        # Send immediately without buffering
        try:
            await self.send(text_data=json.dumps({
                'debug': decorated_output,
                'role': 'system',
                'message_id': f"debug_{self.message_counter}",
                'timestamp': time.time()  # Add timestamp for debugging
            }))
            
            # Also send to the group for consistency
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'debug_message',
                    'message': decorated_output,
                    'message_id': f"debug_{self.message_counter}",
                    'immediate': True  # Flag for immediate processing
                }
            )
            self.message_counter += 1
            
            # Force flush any potential buffers
            await asyncio.sleep(0)  # Yield control to ensure message is sent
            
        except Exception as e:
            logger.error(f"Error sending debug message: {e}")
    
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        
        message = text_data_json['message']
        settings = text_data_json.get('settings', {})  # Get settings from the message
        
        # Send message to room group to indicate typing
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'system_message',
                'message': '🧠 Agent is thinking...',
                'message_id': f"system_{self.message_counter}"
            }
        )
        self.message_counter += 1
        
        # Save user message
        message_obj = await self.save_message(message, 'user')
        
        # Process the message with the agent
        try:
            # Create a task to run the agent query - now returns tuple (response, visualization_files_paths)
            loop = asyncio.get_event_loop()
            response, visualization_files_paths = await loop.run_in_executor(None, self.agent.query, message, settings)
            
            # Save assistant message
            assistant_message = await self.save_message(response, 'assistant')
            
            # Create visualization file URLs if files exist
            visualization_files = None
            if visualization_files_paths:
                visualization_files = {}
                for file_type, file_path in visualization_files_paths.items():
                    if file_path and os.path.exists(file_path):
                        # Create download URL for each file type
                        download_url = f"/api/chats/{self.chat_id}/download_visualization/?type={file_type}"
                        visualization_files[file_type] = {
                            'download_url': download_url,
                            'file_name': os.path.basename(file_path)
                        }
            
            # Send message to room group with visualization files URLs included
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': response,
                    'role': 'assistant',
                    'message_id': str(assistant_message.id),
                    'visualization_files': visualization_files if visualization_files else None
                }
            )
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            error_message = f"Error: {str(e)}\n{traceback.format_exc()}"
            error_msg_obj = await self.save_message(error_message, 'system')
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'system_message',
                    'message': error_message,
                    'message_id': str(error_msg_obj.id)
                }
            )
            
    async def chat_message(self, event):
        message = event['message']
        role = event['role']
        message_id = event.get('message_id', f"auto_{self.message_counter}")
        visualization_files = event.get('visualization_files', None)
        
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'role': role,
            'message_id': message_id,
            'visualization_files': visualization_files
        }))
    
    async def debug_message(self, event):
        message = event['message']
        message_id = event.get('message_id', f"debug_{self.message_counter}")
        
        # Send debug message to WebSocket
        await self.send(text_data=json.dumps({
            'debug': message,
            'role': 'system',
            'message_id': message_id
        }))
    
    async def visualization_files(self, event):
        """Send visualization files information to client"""
        file_types = event['file_types']
        message_id = event.get('message_id', f"vis_files_{self.message_counter}")        
        # Send visualization files info to WebSocket
        await self.send(text_data=json.dumps({
            'visualization_files': file_types,
            'message_id': message_id
        }))
    
    async def system_message(self, event):
        message = event['message']
        message_id = event.get('message_id', f"system_{self.message_counter}")
        
        # Send system message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'role': 'system',
            'message_id': message_id
        }))
        
    @database_sync_to_async
    def save_message(self, content, role):
        """Save a message to the database"""
        chat, _ = Chat.objects.get_or_create(id=self.chat_id)
        
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