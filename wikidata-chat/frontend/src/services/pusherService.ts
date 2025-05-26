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
    // Disable Pusher logging for production
    Pusher.logToConsole = false;

    this.pusher = new Pusher(PUSHER_CONFIG.key, {
      cluster: PUSHER_CONFIG.cluster,
      forceTLS: PUSHER_CONFIG.forceTLS,
      enabledTransports: ['ws', 'wss'],
    });

    // Connection state handlers
    this.pusher.connection.bind('connected', () => {
      this.isConnected = true;
      
      // Handle pending subscription if exists
      if (this.pendingSubscription) {
        const pendingChatId = this.pendingSubscription;
        this.pendingSubscription = null;
        setTimeout(() => this.handleDelayedSubscription(pendingChatId), 100);
      }
    });

    this.pusher.connection.bind('connecting', () => {
      // Connection in progress
    });

    this.pusher.connection.bind('disconnected', () => {
      this.isConnected = false;
    });

    this.pusher.connection.bind('error', (error: any) => {
      console.error('Pusher connection error:', error);
      this.isConnected = false;
    });

    this.pusher.connection.bind('unavailable', () => {
      this.isConnected = false;
    });
  }

  private handleDelayedSubscription(chatId: string) {
    // Retry subscription after connection is established
  }

  subscribeToChat(chatId: string, callbacks: {
    onMessage?: (data: PusherMessage) => void;
    onDebugMessage?: (data: PusherMessage) => void;
    onSystemMessage?: (data: PusherMessage) => void;
    onChatMessage?: (data: PusherMessage) => void;
  }) {
    // If not connected, store the subscription for later
    if (!this.isConnected) {
      this.pendingSubscription = chatId;
      
      // Try again after a delay
      setTimeout(() => {
        if (this.isConnected && this.pendingSubscription === chatId) {
          this.subscribeToChat(chatId, callbacks);
        }
      }, 1000);
      return;
    }

    // Unsubscribe from previous channel if exists
    if (this.currentChannel) {
      this.currentChannel.unbind_all();
      this.pusher.unsubscribe(this.currentChannel.name);
    }

    const channelName = getChatChannelName(chatId);
    this.currentChannel = this.pusher.subscribe(channelName);

    // Subscription handlers (removed detailed logging)
    this.currentChannel.bind('pusher:subscription_succeeded', () => {
      // Successfully subscribed
    });

    this.currentChannel.bind('pusher:subscription_error', (error: any) => {
      console.error('Subscription error:', error);
    });

    // Bind event handlers
    if (callbacks.onMessage) {
      this.currentChannel.bind('message', (data: any) => {
        callbacks.onMessage!(data);
      });
    }

    if (callbacks.onDebugMessage) {
      this.currentChannel.bind('debug_message', (data: any) => {
        callbacks.onDebugMessage!(data);
      });
    }

    if (callbacks.onSystemMessage) {
      this.currentChannel.bind('system_message', (data: any) => {
        callbacks.onSystemMessage!(data);
      });
    }

    if (callbacks.onChatMessage) {
      this.currentChannel.bind('chat_message', (data: any) => {
        callbacks.onChatMessage!(data);
      });
    }
  }

  unsubscribeFromChat() {
    if (this.currentChannel) {
      this.currentChannel.unbind_all();
      this.pusher.unsubscribe(this.currentChannel.name);
      this.currentChannel = null;
    }
    this.pendingSubscription = null;
  }

  disconnect() {
    this.unsubscribeFromChat();
    this.pusher.disconnect();
    this.isConnected = false;
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
