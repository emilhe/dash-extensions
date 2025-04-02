import React, { useEffect, useRef, ReactNode } from 'react';
import { DashComponentProps } from '../props';

export type Props = DashComponentProps & {
  /**
   * Events for which to call preventDefault() during loading.
   */
  preventDefault?: string[];
  /**
   * Array or single React node.
   */
  children?: ReactNode;
  /**
   * Object that holds the loading state coming from dash-renderer.
   */
  loading_state?: {
    /**
     * Determines if the component is loading or not.
     */
    is_loading?: boolean;
    /**
     * Holds which property is loading.
     */
    prop_name?: string;
    /**
     * Holds the name of the component that is loading.
     */
    component_name?: string;
  };
};

/**
 * The Loading component makes it possible to stop event propagation during loading.
 */
const Loading = ({
  children,
  loading_state,
  preventDefault = ['keydown'],
}: Props) => {
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const current = container.current;
    const handlePreventDefault = (e: Event) => {
      e.preventDefault();
    };

    if (current) {
      const isLoading = loading_state && loading_state.is_loading;
      if (!isLoading) {
        preventDefault.forEach((event) => {
          current.removeEventListener(event, handlePreventDefault, true);
        });
      } else {
        preventDefault.forEach((event) => {
          current.addEventListener(event, handlePreventDefault, true);
        });
      }
    }

    return () => {
      if (current) {
        preventDefault.forEach((event) => {
          current.removeEventListener(event, handlePreventDefault, true);
        });
      }
    };
  }, [loading_state, preventDefault]);

  return <div ref={container}>{children}</div>;
};

(Loading as any)._dashprivate_isLoadingComponent = true;

export default Loading;
