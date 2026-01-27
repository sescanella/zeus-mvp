// zeues-frontend/lib/hooks/useSSE.ts
// React hook for EventSource SSE with mobile lifecycle management

import { useEffect, useState, useRef, useCallback } from 'react';
import type { SSEEvent, UseSSEOptions } from '../types';

const MAX_RETRIES = 10;
const MAX_DELAY = 30000;  // 30 seconds

export function useSSE(url: string, options: UseSSEOptions) {
  const [isConnected, setIsConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const retryCountRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const updateConnectionStatus = useCallback((connected: boolean) => {
    setIsConnected(connected);
    options.onConnectionChange?.(connected);
  }, [options]);

  const connect = useCallback(() => {
    // Clean up existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const es = new EventSource(url);

    es.onopen = () => {
      updateConnectionStatus(true);
      retryCountRef.current = 0;  // Reset retry counter on success
    };

    es.addEventListener('spool_update', (event: MessageEvent) => {
      try {
        const data: SSEEvent = JSON.parse(event.data);
        options.onMessage(data);
      } catch (error) {
        console.error('Failed to parse SSE event:', error);
      }
    });

    es.onerror = (error: Event) => {
      updateConnectionStatus(false);
      es.close();

      // Exponential backoff with max cap
      const delay = Math.min(
        1000 * Math.pow(2, retryCountRef.current),
        MAX_DELAY
      );

      if (retryCountRef.current < MAX_RETRIES) {
        retryCountRef.current += 1;
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, delay);
      } else {
        // Max retries exceeded
        options.onError?.(error);
      }
    };

    eventSourceRef.current = es;
  }, [url, options, updateConnectionStatus]);

  useEffect(() => {
    // Initial connection
    connect();

    // Page Visibility API integration
    const handleVisibilityChange = () => {
      if (options.openWhenHidden !== true) {  // Default behavior: close on hidden
        if (document.hidden) {
          // Page hidden (backgrounded) - close connection to save resources
          eventSourceRef.current?.close();
          updateConnectionStatus(false);

          // Clear any pending reconnect
          if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
          }
        } else {
          // Page visible again - reconnect immediately
          retryCountRef.current = 0;  // Reset retry count
          connect();
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    // Cleanup on unmount
    return () => {
      eventSourceRef.current?.close();
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [url, options.openWhenHidden, connect, updateConnectionStatus]);

  const disconnect = useCallback(() => {
    eventSourceRef.current?.close();
    updateConnectionStatus(false);
  }, [updateConnectionStatus]);

  return {
    isConnected,
    disconnect
  };
}
