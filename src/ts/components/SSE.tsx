import React, { Suspense } from 'react';
import { SSEOptions } from 'sse.js';
import { DashComponentProps } from '../props';

const LazySSE = React.lazy(() => import(/* webpackChunkName: "SSE" */ '../fragments/SSE'));

export type Props = DashComponentProps & {
  /**
   * Options passed to the SSE constructor.
   */
  options?: SSEOptions;
  /**
   * URL of the endpoint.
   */
  url?: string;
  /**
   * A boolean indicating if the stream values should be concatenated.
   */
  concat?: boolean;
  /**
   * If set, each character is delayed by some amount of time. Used to animate the stream.
   */
  animate_delay?: number;
  /**
   * Chunk size (i.e. number of characters) for the animation.
   */
  animate_chunk?: number;
  /**
   * Prefix to be excluded from the animation.
   */
  animate_prefix?: string;
  /**
   * Suffix to be excluded from the animation.
   */
  animate_suffix?: string;
  /**
   * The data value. Either the latest, or the concatenated depending on the `concat` property.
   */
  value?: string;
  /**
   * The animation of the data.
   */
  animation?: string;
  /**
   * A boolean indicating if the (current) stream has ended.
   */
  done?: boolean;
};

/**
 * The SSE component makes it possible to collect data from e.g. a ResponseStream. It's a wrapper around the SSE.js library.
 * https://github.com/mpetazzoni/sse.js
 */
const SSE = (props: Props) => {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <LazySSE {...props} />
    </Suspense>
  );
};

export default SSE;
