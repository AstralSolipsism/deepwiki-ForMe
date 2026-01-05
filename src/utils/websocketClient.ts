/**
 * WebSocket client for chat completions
 * This replaces the HTTP streaming endpoint with a WebSocket connection
 */

const DEFAULT_SERVER_BASE_URL = 'http://localhost:8001';

const getServerBaseUrl = (): string => {
  const env = (globalThis as unknown as { process?: { env?: { SERVER_BASE_URL?: string } } }).process?.env;
  return env?.SERVER_BASE_URL || DEFAULT_SERVER_BASE_URL;
};

const toWebSocketBaseUrl = (baseUrl: string): string => {
  return baseUrl.replace(/^https:/, 'wss:').replace(/^http:/, 'ws:');
};

const isLoopbackHost = (hostname: string): boolean => {
  return hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '::1';
};

/**
 * Get the WebSocket URL for chat completions
 * In browser environment, uses the current page's domain and protocol
 * In server environment (SSR), falls back to environment variable or default
 */
export function getWebSocketUrl(): string {
  // Check if we're in a browser environment
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;

    // Local development: backend is usually on a different port (e.g. 8001),
    // so prefer SERVER_BASE_URL (or default) to avoid connecting to the Next.js port.
    if (isLoopbackHost(window.location.hostname)) {
      const wsBaseUrl = toWebSocketBaseUrl(getServerBaseUrl());
      return `${wsBaseUrl}/ws/chat`;
    }

    return `${protocol}//${host}/ws/chat`;
  }

  // Server-side fallback (for SSR or build time)
  const wsBaseUrl = toWebSocketBaseUrl(getServerBaseUrl());
  return `${wsBaseUrl}/ws/chat`;
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface ChatCompletionRequest {
  repo_url: string;
  messages: ChatMessage[];
  filePath?: string;
  token?: string;
  type?: string;
  provider?: string;
  model?: string;
  language?: string;
  excluded_dirs?: string;
  excluded_files?: string;
}

/**
 * Creates a WebSocket connection for chat completions
 * @param request The chat completion request
 * @param onMessage Callback for received messages
 * @param onError Callback for errors
 * @param onClose Callback for when the connection closes
 * @returns The WebSocket connection
 */
export const createChatWebSocket = (
  request: ChatCompletionRequest,
  onMessage: (message: string) => void,
  onError: (error: Event) => void,
  onClose: () => void
): WebSocket => {
  // Create WebSocket connection
  const ws = new WebSocket(getWebSocketUrl());
  
  // Set up event handlers
  ws.onopen = () => {
    console.log('WebSocket connection established');
    // Send the request as JSON
    ws.send(JSON.stringify(request));
  };
  
  ws.onmessage = (event) => {
    // Call the message handler with the received text
    onMessage(event.data);
  };
  
  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    onError(error);
  };
  
  ws.onclose = () => {
    console.log('WebSocket connection closed');
    onClose();
  };
  
  return ws;
};

/**
 * Closes a WebSocket connection
 * @param ws The WebSocket connection to close
 */
export const closeWebSocket = (ws: WebSocket | null): void => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.close();
  }
};
