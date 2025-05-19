# backend/chat/consumers.py
import json
import traceback
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Chat, Message
import asyncio
import os
import uuid

# Import the Wikidata Agent
from agent.agent import WikidataAgent

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
        
        # Initialize the agent with a callback for debug output
        self.agent = WikidataAgent(gemini_api_key=gemini_api_key, debug_callback=self.debug_callback)
        
        # Add a message counter to prevent duplicate message issues
        self.message_counter = 0
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    @database_sync_to_async
    def chat_exists(self, chat_id):
        """Check if a chat with the given ID exists"""
        try:
            return Chat.objects.filter(id=chat_id).exists()
        except Exception:
            return False
    
    @database_sync_to_async
    def create_chat(self, chat_id):
        """Create a new chat with the specified ID"""
        try:
            # Try to convert the chat_id string to a UUID object
            chat_uuid = uuid.UUID(chat_id)
            return Chat.objects.create(id=chat_uuid, title="New Chat")
        except Exception as e:
            print(f"Error creating chat: {e}")
            return None
    
    async def debug_callback(self, output):
        """Callback function for agent debugging output"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'debug_message',
                'message': output,
                'message_id': f"debug_{self.message_counter}"
            }
        )
        self.message_counter += 1
    
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        
        # Check if this is a file request
        if 'file_request' in text_data_json:
            await self.handle_file_request(text_data_json['file_request'])
            return
            
        message = text_data_json['message']
        
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
            # Create a task to run the agent query
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, self.agent.query, message)
            
            # Save assistant message
            assistant_message = await self.save_message(response, 'assistant')
            
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': response,
                    'role': 'assistant',
                    'message_id': str(assistant_message.id)
                }
            )
            
            # Send visualization file info to client if available
            if hasattr(self.agent, 'visualization_files') and self.agent.visualization_files:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'visualization_files',
                        'file_types': {k: v is not None for k, v in self.agent.visualization_files.items()},
                        'message_id': f"vis_files_{self.message_counter}"
                    }
                )
                self.message_counter += 1
                
        except Exception as e:
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
            
    async def handle_file_request(self, file_type):
        """Handle requests for visualization files"""
        if not hasattr(self.agent, 'visualization_files') or not self.agent.visualization_files:
            await self.send(text_data=json.dumps({
                'file_error': 'No visualization files available',
                'file_type': file_type
            }))
            return
            
        file_path = self.agent.visualization_files.get(file_type)
        if not file_path or not os.path.exists(file_path):
            await self.send(text_data=json.dumps({
                'file_error': f'File of type {file_type} not found',
                'file_type': file_type
            }))
            return
            
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
                
            # Send file content to client
            await self.send(text_data=json.dumps({
                'file_content': file_content,
                'file_type': file_type,
                'file_name': os.path.basename(file_path)
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'file_error': f'Error reading file: {str(e)}',
                'file_type': file_type
            }))
    
    async def chat_message(self, event):
        message = event['message']
        role = event['role']
        message_id = event.get('message_id', f"auto_{self.message_counter}")
        
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'role': role,
            'message_id': message_id
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