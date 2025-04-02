import { useEffect, useRef } from 'react';
import { DashComponentProps } from '../props';

export type Props = DashComponentProps & {
  /**
   * This websocket state (in the readyState prop) and associated information.
   */
  state?: any;
  /**
   * When messages are received, this property is updated with the message content.
   */
  message?: any;
  /**
   * This property is set with the content of the onerror event.
   */
  error?: any;
  /**
   * When this property is set, a message is sent with its content.
   */
  send?: any;
  /**
   * The websocket endpoint (e.g. wss://echo.websocket.org).
   */
  url?: string;
  /**
   * Supported websocket protocols (optional).
   */
  protocols?: string[];
  /**
   * How many ms to wait for websocket to be ready when sending a message (optional).
   */
  timeout?: number;
};

/**
 * A simple interface to the WebSocket API.
 */
const DashWebSocket = ({
  url,
  protocols,
  timeout = 1000,
  send,
  setProps,
  state = { readyState: WebSocket.CLOSED },
}: Props) => {
  const clientRef = useRef<WebSocket | null>(null);
  const prevSendRef = useRef<any>();

  const initClient = () => {
    if (!url) {
      return;
    }
    const ws = new WebSocket(url, protocols);
    clientRef.current = ws;
    // Set initial state to CONNECTING.
    if (setProps) {
      setProps({ state: { readyState: WebSocket.CONNECTING } });
    }
    ws.onopen = (e) => {
      if (setProps) {
        setProps({
          state: {
            readyState: WebSocket.OPEN,
            isTrusted: e.isTrusted,
            timeStamp: e.timeStamp,
            origin: (e as any).origin,  // TODO: Is this correct?
          },
        });
      }
    };
    ws.onmessage = (e) => {
      if (setProps) {
        setProps({
          message: {
            data: e.data,
            isTrusted: e.isTrusted,
            origin: e.origin,
            timeStamp: e.timeStamp,
          },
        });
      }
    };
    ws.onerror = (e) => {
      if (setProps) {
        setProps({ error: JSON.stringify(e) });
      }
    };
    ws.onclose = (e) => {
      if (setProps) {
        setProps({
          state: {
            readyState: WebSocket.CLOSED,
            isTrusted: e.isTrusted,
            timeStamp: e.timeStamp,
            code: e.code,
            reason: e.reason,
            wasClean: e.wasClean,
          },
        });
      }
    };
  };

  const destroyClient = () => {
    if (clientRef.current) {
      clientRef.current.onopen = null;
      clientRef.current.onmessage = null;
      clientRef.current.onerror = null;
      clientRef.current.onclose = null;
      clientRef.current.close();
      clientRef.current = null;
    }
  };

  // Initialize the websocket on mount and when the URL changes.
  useEffect(() => {
    // When URL changes, (re)initialize the client.
    destroyClient();
    if (url) {
      initClient();
      // Wait briefly for the connection to settle.
      const timer = setTimeout(() => {}, 100);
      return () => clearTimeout(timer);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url, protocols]);

  // Send message when the 'send' prop changes.
  useEffect(() => {
    // Only send if send has changed.
    if (prevSendRef.current === send) {
      return;
    }
    prevSendRef.current = send;
    if (!send || !setProps) return;

    (async () => {
      // If connection is closed, try reconnecting.
      if (state.readyState === WebSocket.CLOSED) {
        console.log('Websocket CLOSED. Attempting to reconnect...');
        destroyClient();
        initClient();
        await new Promise((r) => setTimeout(r, 100));
      }
      // If connection is connecting, wait for the timeout.
      if (state.readyState === WebSocket.CONNECTING) {
        console.log('Websocket CONNECTING. Delaying sending message...');
        await new Promise((r) => setTimeout(r, timeout));
      }
      // If the connection is open, send the message.
      if (state.readyState === WebSocket.OPEN && clientRef.current) {
        clientRef.current.send(send);
        return;
      }
      console.log('Websocket connection failed. Aborting.');
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [send, state.readyState, timeout]);

  // Clean up on unmount.
  useEffect(() => {
    return () => {
      destroyClient();
    };
  }, []);

  return null;
};

export default DashWebSocket;
