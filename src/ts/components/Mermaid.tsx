import React, { Suspense } from 'react';
import { DashComponentProps } from '../props';

const LazyMermaid = React.lazy(() => import(/* webpackChunkName: "Mermaid" */ '../fragments/Mermaid'));

export type Props = DashComponentProps & {
  /**
   * The mermaid code of your chart. Check Mermaid js documentation for details.
   */
  chart?: string;

  /**
   * An optional name of your mermaid diagram/flowchart/gantt etc.
   */
  name?: string;

  /**
   * An optional object with one of several Mermaid config parameters.
   * Check Mermaid js documentation for details.
   */
  config?: Record<string, any>;
  
  /**
   * The class of the component.
   */
  className?: string;
};

/**
 * Light wrapper of the react-lottie component for Dash.
 */
const Mermaid = (props: Props) => {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <LazyMermaid {...props} />
    </Suspense>
  );
};

export default Mermaid;
