# backend/chat/pusher_service.py
import pusher
from django.conf import settings
import logging
import json
import time

logger = logging.getLogger(__name__)

class PusherService:
    """Service for handling Pusher notifications"""
    
    def __init__(self):
        self.pusher_client = pusher.Pusher(
            app_id=settings.PUSHER_APP_ID,
            key=settings.PUSHER_KEY,
            secret=settings.PUSHER_SECRET,
            cluster=settings.PUSHER_CLUSTER,
            ssl=True
        )
        logger.info("Initialized PusherService")
    
    def get_channel_name(self, chat_id):
        """Get channel name for a chat"""
        return f'chat_{chat_id}'
    
    def send_message(self, chat_id, message_data):
        """Send a message to a chat channel"""
        try:
            channel = self.get_channel_name(chat_id)
            logger.info(f"Sending message to channel {channel}: {json.dumps(message_data, indent=2)}")
            self.pusher_client.trigger(channel, 'message', message_data)
            logger.info(f"✅ Sent message to channel {channel}")
        except Exception as e:
            logger.error(f"❌ Error sending message via Pusher: {e}")
    
    def send_debug_message(self, chat_id, debug_content):
        """Send a debug message to a chat channel"""
        try:
            channel = self.get_channel_name(chat_id)
            debug_data = {
                'debug': debug_content,
                'role': 'system',
                'message_id': f"debug_{int(time.time() * 1000)}",
                'timestamp': time.time()
            }
            logger.info(f"🐛 Sending debug message to channel {channel}: {debug_content[:100]}...")
            self.pusher_client.trigger(channel, 'debug_message', debug_data)
            logger.info(f"✅ Sent debug message to channel {channel}")
        except Exception as e:
            logger.error(f"❌ Error sending debug message via Pusher: {e}")
    
    def send_system_message(self, chat_id, content):
        """Send a system message to a chat channel"""
        try:
            channel = self.get_channel_name(chat_id)
            system_data = {
                'message': content,
                'role': 'system',
                'message_id': f"system_{int(time.time() * 1000)}",
                'timestamp': time.time()
            }
            logger.info(f"🔧 Sending system message to channel {channel}: {content[:100]}...")
            self.pusher_client.trigger(channel, 'system_message', system_data)
            logger.info(f"✅ Sent system message to channel {channel}")
        except Exception as e:
            logger.error(f"❌ Error sending system message via Pusher: {e}")
    
    def send_chat_message(self, chat_id, role, content, message_id=None, visualization_files=None):
        """Send a chat message to a chat channel"""
        try:
            channel = self.get_channel_name(chat_id)
            message_data = {
                'message': content,
                'role': role,
                'message_id': message_id or f"{role}_{int(time.time() * 1000)}",
                'timestamp': time.time()
            }
            if visualization_files:
                message_data['visualization_files'] = visualization_files
            
            logger.info(f"💬 Sending {role} message to channel {channel}: {content[:100]}...")
            if visualization_files:
                logger.info(f"📎 Including visualization files: {list(visualization_files.keys())}")
            
            self.pusher_client.trigger(channel, 'chat_message', message_data)
            logger.info(f"✅ Sent chat message to channel {channel}")
        except Exception as e:
            logger.error(f"❌ Error sending chat message via Pusher: {e}")

# Global pusher service instance
pusher_service = PusherService()
