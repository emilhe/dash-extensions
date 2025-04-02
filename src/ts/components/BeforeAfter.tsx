import React, { Suspense } from 'react';
import { DashComponentProps } from '../props';

const LazyBeforeAfter = React.lazy(() => import(/* webpackChunkName: "BeforeAfter" */ '../fragments/BeforeAfter'));

export type Props = DashComponentProps & {
  /** Image height — default "auto" for responsive images */
  height?: string;

  /** Image width — default "100%" for responsive images */
  width?: string;

  /** Automatic slide on mouse over */
  hover?: boolean;

  /** The divider position can be specified as a percentage, i.e. 0 to 100 */
  value?: number;

  /** Set slider direction */
  direction?: 'horizontal' | 'vertical';

  /** Enable/disable slider position control with the keyboard */
  keyboard?: 'enabled' | 'disabled';

  /** Props for the `before` Img component. eg {"src": "/assets/lena_bw.png"} */
  before?: object;

  /** Props for the `after` Img component. eg {"src": "/assets/lena_color.png"} */
  after?: object;
}

/**
 * BeforeAfter — A before‑and‑after image slider built on img-comparison-slider.
 *
 */
const BeforeAfter = (props: Props) => {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <LazyBeforeAfter {...props} />
    </Suspense>
  );
};

export default BeforeAfter;