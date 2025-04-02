import { useEffect, useRef, useCallback, ReactNode } from 'react';
import { DashComponentProps } from '../props';
import React from 'react';

export type Props = DashComponentProps & {
  /**
   * The children of this component. If any children are provided, the component will listen for events from these
   * components. If no children are specified, the component will listen for events from the document object.
   */
  children?: ReactNode;
  /**
   * The CSS style of the component.
   */
  style?: React.CSSProperties;
  /**
   * A custom class name.
   */
  className?: string;
  /**
   * The event properties to forward to Dash, see https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent.
   */
  eventProps?: string[];
  /**
   * The keys to capture. Defaults to all keys. Can be either a string (e.g. "Enter") or an object (e.g. {key: 'Enter', ctrlKey: true}).
   */
  captureKeys?: Array<string | Record<string, any>>;
  /**
   * The result of the key down event.
   */
  keydown?: Record<string, any>;
  /**
   * The result of the key up event.
   */
  keyup?: Record<string, any>;
  /**
   * A dict of objects like keydown for all keys currently pressed.
   */
  keys_pressed?: Record<string, any>;
  /**
   * A counter, which is incremented on each key down event.
   */
  n_keydowns?: number;
  /**
   * A counter, which is incremented on each key up event.
   */
  n_keyups?: number;
  /**
   * Value of useCapture used when registering event listeners.
   */
  useCapture?: boolean;
};

/**
 * A component that listens for keyboard events and forwards them to Dash.
 */
const Keyboard = ({
  children,
  style,
  className,
  eventProps = ["key", "altKey", "ctrlKey", "shiftKey", "metaKey", "repeat"],
  captureKeys,
  setProps,
  keys_pressed = {},
  n_keydowns = 0,
  n_keyups = 0,
  useCapture = false,
}: Props) => {
  const containerRef = useRef<HTMLDivElement>(null);

  const filterEvents = useCallback((event: KeyboardEvent): boolean => {
    // If no captureKeys are specified, capture all events.
    if (!captureKeys || captureKeys.length === 0) return true;
    for (const captureKey of captureKeys) {
      if (typeof captureKey === 'string') {
        if (captureKey === event.key) {
          return true;
        }
        continue;
      }
      let fullMatch = true;
      for (const [key, value] of Object.entries(captureKey)) {
        fullMatch = fullMatch && event[key as keyof KeyboardEvent] === value;
      }
      if (fullMatch) return true;
    }
    return false;
  }, [captureKeys]);

  const keydownHandler = useCallback((event: KeyboardEvent) => {
    if (!filterEvents(event)) return;
    const keydownData = eventProps.reduce((acc, prop) => {
      acc[prop] = (event as any)[prop];
      return acc;
    }, {} as Record<string, any>);
    if (setProps) {
      setProps({ keydown: keydownData });
      setProps({ n_keydowns: n_keydowns + 1 });
      if (keydownData.key) {
        const newKeysPressed = { ...keys_pressed };
        newKeysPressed[keydownData.key] = keydownData;
        setProps({ keys_pressed: newKeysPressed });
      }
    }
  }, [filterEvents, eventProps, keys_pressed, n_keydowns, setProps]);

  const keyupHandler = useCallback((event: KeyboardEvent) => {
    if (!filterEvents(event)) return;
    const keyupData = eventProps.reduce((acc, prop) => {
      acc[prop] = (event as any)[prop];
      return acc;
    }, {} as Record<string, any>);
    if (setProps) {
      setProps({ keyup: keyupData });
      setProps({ n_keyups: n_keyups + 1 });
      if (keyupData.key) {
        const newKeysPressed = { ...keys_pressed };
        delete newKeysPressed[event.key];
        setProps({ keys_pressed: newKeysPressed });
      }
    }
  }, [filterEvents, eventProps, keys_pressed, n_keyups, setProps]);

  useEffect(() => {
    const container = containerRef.current;
    const sources: EventTarget[] = container && container.children.length > 0
      ? Array.from(container.children)
      : [document];
    sources.forEach(source => {
      source.addEventListener("keydown", keydownHandler, useCapture);
      source.addEventListener("keyup", keyupHandler, useCapture);
    });
    return () => {
      sources.forEach(source => {
        source.removeEventListener("keydown", keydownHandler, useCapture);
        source.removeEventListener("keyup", keyupHandler, useCapture);
      });
    };
  }, [keydownHandler, keyupHandler, useCapture]);

  return (
    <div className={className} style={style} ref={containerRef}>
      {children}
    </div>
  );
};

export default Keyboard;
