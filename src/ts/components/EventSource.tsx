import { useEffect, useRef } from 'react';
import { DashComponentProps } from '../props';

export type Props = DashComponentProps & {
  /**
   * Close event source.
   */
  close?: boolean;
  /**
   * Error.
   */
  error?: string;
  /**
   * Received message.
   */
  message?: string;
  /**
   * A number representing the state of the connection. Possible values are CONNECTING (0), OPEN (1), or CLOSED (2).
   */
  readyState?: 0 | 1 | 2;
  /**
   * A boolean value indicating whether the EventSource object was instantiated with cross-origin (CORS) credentials set (true), or not (false, the default).
   */
  withCredentials?: boolean;
  /**
   * A DOMString representing the URL of the source.
   */
  url: string;
};

/**
 * An interface to server sent events in Dash.
 */
const DashEventSource = ({
  close,
  setProps,
  withCredentials = false,
  url,
}: Props) => {
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const es = new EventSource(url, { withCredentials });
    eventSourceRef.current = es;

    es.onopen = () => {
      if (setProps) {
        setProps({ readyState: EventSource.OPEN });
      }
    };

    es.onmessage = (event) => {
      if (setProps) {
        setProps({ message: event.data });
      }
    };

    es.onerror = (event) => {
      if (setProps) {
        setProps({ error: JSON.stringify(event) });
      }
    };

    // Cleanup on unmount
    return () => {
      es.close();
    };
  }, [url, withCredentials, setProps]);

  useEffect(() => {
    if (close && eventSourceRef.current) {
      eventSourceRef.current.close();
      if (setProps) {
        setProps({ readyState: EventSource.CLOSED });
      }
    }
  }, [close, setProps]);

  return null;
};

export default DashEventSource;
