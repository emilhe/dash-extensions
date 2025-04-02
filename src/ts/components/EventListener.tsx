import React, { useEffect, useRef, ReactNode } from 'react';
import { DashComponentProps } from '../props';

export type Props = DashComponentProps & {
  /**
   * The event entry specifies which event to listen to, e.g. "click" for click events.
   * The "props" entry specifies what event properties to record, e.g. ["x", "y"] to get the cursor position.
   */
  events?: Array<{
    event: string;
    props?: string[];
  }>;
  /**
   * If true, event information is logged to the javascript console.
   */
  logging?: boolean;
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
   * The latest event fired.
   */
  event?: object;
  /**
   * The number of events fired.
   */
  n_events?: number;
  /**
   * Value of useCapture used when registering event listeners.
   */
  useCapture?: boolean;
};

/**
 * A component that listens for events and forwards them to Dash.
 */
const EventListener = ({
  events = [
    {
      event: 'keydown',
      props: ['key', 'altKey', 'ctrlKey', 'shiftKey', 'metaKey', 'repeat']
    }
  ],
  logging = false,
  children,
  style,
  className,
  setProps,
  n_events = 0,
  useCapture = false
}: Props) => {
  const containerRef = useRef<HTMLDivElement>(null);
  let sources: Array<EventTarget> = [];

  const getSources = (): EventTarget[] => {
    const current = containerRef.current;
    let srcs: EventTarget[] = [];
    if (current && current.children && current.children.length > 0) {
      srcs = Array.from(current.children);
    } else {
      srcs = [document];
    }
    return srcs;
  };

  const getDescendantProp = (obj: any, desc: string): any => {
    const arr = desc.split(".");
    while(arr.length && (obj = obj[arr.shift()]));
    return obj;
  }

  const eventHandler = (e: Event) => {
    if (logging) {
      console.log(e);
    }
    const matching = events.find(o => o.event === e.type);
    const eventProps = matching && matching.props ? matching.props : [];
    const eventData = eventProps.reduce((acc, key) => {
      acc[key] = getDescendantProp(e, key);
      return acc;
    }, {} as Record<string, any>);
    if (setProps) {
      // Increment the number of events fired
      setProps({ n_events: n_events + 1 });
      // Set the event data for Dash callbacks
      setProps({ event: eventData });
    }
  };

  useEffect(() => {
    const eventTypes = events.map(o => o.event);
    sources = getSources();
    sources.forEach(source => {
      eventTypes.forEach(evType => {
        source.addEventListener(evType, eventHandler, useCapture);
      });
    });

    return () => {
      sources.forEach(source => {
        eventTypes.forEach(evType => {
          source.removeEventListener(evType, eventHandler, useCapture);
        });
      });
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [events, logging, n_events, useCapture, setProps]);

  return (
    <div className={className} style={style} ref={containerRef}>
      {children}
    </div>
  );
};

export default EventListener;
