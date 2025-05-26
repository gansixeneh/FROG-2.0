// frontend/src/services/pusherService.ts
import Pusher from 'pusher-js';
import { PUSHER_CONFIG, getChatChannelName } from '../config/api';

export interface PusherMessage {
  message?: string;
  debug?: string;
  role: 'user' | 'assistant' | 'system';
  message_id: string;
  timestamp: number;
  visualization_files?: any;
}

export class PusherService {
  private pusher: Pusher;
  private currentChannel: any = null;
  private isConnected: boolean = false;
  private pendingSubscription: string | null = null;

  constructor() {
    // Enable Pusher logging for debugging
    Pusher.logToConsole = true;
    
    console.log('🚀 Initializing Pusher with config:', {
      key: PUSHER_CONFIG.key,
      cluster: PUSHER_CONFIG.cluster,
      forceTLS: PUSHER_CONFIG.forceTLS
    });

    this.pusher = new Pusher(PUSHER_CONFIG.key, {
      cluster: PUSHER_CONFIG.cluster,
      forceTLS: PUSHER_CONFIG.forceTLS,
      enabledTransports: ['ws', 'wss'],
    });

    // Log connection state changes
    this.pusher.connection.bind('connected', () => {
      console.log('✅ Pusher connected successfully');
      this.isConnected = true;
      
      // If there was a pending subscription, handle it now
      if (this.pendingSubscription) {
        console.log('🔄 Processing pending subscription:', this.pendingSubscription);
        const pendingChatId = this.pendingSubscription;
        this.pendingSubscription = null;
        // Re-trigger subscription now that we're connected
        setTimeout(() => this.handleDelayedSubscription(pendingChatId), 100);
      }
    });

    this.pusher.connection.bind('connecting', () => {
      console.log('🔄 Pusher connecting...');
    });

    this.pusher.connection.bind('disconnected', () => {
      console.log('❌ Pusher disconnected');
      this.isConnected = false;
    });

    this.pusher.connection.bind('error', (error: any) => {
      console.error('❌ Pusher connection error:', error);
      this.isConnected = false;
    });

    this.pusher.connection.bind('unavailable', () => {
      console.error('❌ Pusher connection unavailable');
      this.isConnected = false;
    });
  }

  private handleDelayedSubscription(chatId: string) {
    console.log('🔄 Retrying subscription for chat:', chatId);
    // This will be called by the component again
  }

  subscribeToChat(chatId: string, callbacks: {
    onMessage?: (data: PusherMessage) => void;
    onDebugMessage?: (data: PusherMessage) => void;
    onSystemMessage?: (data: PusherMessage) => void;
    onChatMessage?: (data: PusherMessage) => void;
  }) {
    console.log('📡 Subscribe request for chat:', chatId, 'Connected:', this.isConnected);

    // If not connected, store the subscription for later
    if (!this.isConnected) {
      console.log('⏳ Pusher not connected yet, storing subscription for later');
      this.pendingSubscription = chatId;
      
      // Try again after a delay
      setTimeout(() => {
        if (this.isConnected && this.pendingSubscription === chatId) {
          console.log('🔄 Retrying subscription after connection established');
          this.subscribeToChat(chatId, callbacks);
        }
      }, 1000);
      return;
    }

    // Unsubscribe from previous channel if exists
    if (this.currentChannel) {
      console.log('🔄 Unsubscribing from previous channel:', this.currentChannel.name);
      this.currentChannel.unbind_all();
      this.pusher.unsubscribe(this.currentChannel.name);
    }

    const channelName = getChatChannelName(chatId);
    console.log('📡 Subscribing to Pusher channel:', channelName);
    
    this.currentChannel = this.pusher.subscribe(channelName);

    // Log subscription success/error
    this.currentChannel.bind('pusher:subscription_succeeded', () => {
      console.log('✅ Successfully subscribed to channel:', channelName);
    });

    this.currentChannel.bind('pusher:subscription_error', (error: any) => {
      console.error('❌ Subscription error for channel:', channelName, error);
    });

    // Bind event handlers with detailed logging
    if (callbacks.onMessage) {
      this.currentChannel.bind('message', (data: any) => {
        console.log('📨 Received message event:', data);
        callbacks.onMessage!(data);
      });
    }

    if (callbacks.onDebugMessage) {
      this.currentChannel.bind('debug_message', (data: any) => {
        console.log('🐛 Received debug_message event:', data);
        callbacks.onDebugMessage!(data);
      });
    }

    if (callbacks.onSystemMessage) {
      this.currentChannel.bind('system_message', (data: any) => {
        console.log('🔧 Received system_message event:', data);
        callbacks.onSystemMessage!(data);
      });
    }

    if (callbacks.onChatMessage) {
      this.currentChannel.bind('chat_message', (data: any) => {
        console.log('💬 Received chat_message event:', data);
        callbacks.onChatMessage!(data);
      });
    }

    console.log(`✅ Event handlers bound for channel: ${channelName}`);
  }

  unsubscribeFromChat() {
    if (this.currentChannel) {
      console.log('🔄 Unsubscribing from channel:', this.currentChannel.name);
      this.currentChannel.unbind_all();
      this.pusher.unsubscribe(this.currentChannel.name);
      this.currentChannel = null;
      console.log('✅ Unsubscribed from Pusher channel');
    }
    this.pendingSubscription = null;
  }

  disconnect() {
    this.unsubscribeFromChat();
    this.pusher.disconnect();
    this.isConnected = false;
    console.log('🔌 Pusher disconnected');
  }

  // Method to check connection status
  getConnectionStatus() {
    return {
      isConnected: this.isConnected,
      connectionState: this.pusher.connection.state,
      currentChannel: this.currentChannel?.name || null
    };
  }
}

// Global pusher service instance
export const pusherService = new PusherService();
