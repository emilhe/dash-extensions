import React, { Suspense } from 'react';
import { DashComponentProps } from '../props';

const LazyLottie = React.lazy(() => import(/* webpackChunkName: "Lottie" */ '../fragments/Lottie'));

export type Props = DashComponentProps & {

  /**
   * If set, data will be downloaded from this URL.
   */
  url?: string;
  
  /**
   * Animation speed. 1 is normal speed (and default).
   */
  speed?: number;

  /**
   * Actions routed to the Lottie component to control the animation state.
   */
  action?: 'play' | 'pause' | 'stop';

  /**
   * Options passed to the Lottie animation (see https://github.com/Gamote/lottie-react for details).
   */
  options?: object;

}

/**
 * Light wrapper of the lottie-react component for Dash.
 */
const Lottie = (props: Props) => {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <LazyLottie {...props} />
    </Suspense>
  );
};

export default Lottie;
