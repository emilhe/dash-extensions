import React, { Suspense } from "react";
import { DashComponentProps } from "../props";

const LazyPurify = React.lazy(() => import(/* webpackChunkName: "Purify" */ '../fragments/Purify'));

export type Props = DashComponentProps & {
  /**
   * Html string.
   */
  html?: string;
  /**
   * Configuration (optional) of DOMPurify, see the docs https://github.com/cure53/DOMPurify.
   */
  config?: Record<string, any>;
  /**
   * The class of the component.
   */
  className?: string;
};


/**
 * A simple component that displays HTML in a safe way via DOMPurify.
 */
const Purify = (props: Props) => {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <LazyPurify {...props} />
    </Suspense>
  );
};

export default Purify;
