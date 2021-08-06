import React, { Suspense } from 'react';
import PropTypes from "prop-types";

const LazyLottie = React.lazy(() => import(/* webpackChunkName: "lottie" */ '../fragments/Lottie.react'));

const Lottie = (props) => {
  return (
    <div>
      <Suspense fallback={<div>Loading...</div>}>
        <LazyLottie {...props} />
      </Suspense>
    </div>
  );
}

Lottie.propTypes = {

    /**
     * The ID used to identify this component in Dash callbacks
     */
    id: PropTypes.string,

    /**
     * The children of this component
     */
    children: PropTypes.node,

    /**
     * The class of the component
     */
    className: PropTypes.string,

    /**
     * Options passed to the Lottie animation (see https://www.npmjs.com/package/react-lottie for details)
     */
    options: PropTypes.object,

    /**
     * If set, data will be downloaded from this url.
     */
    url: PropTypes.string,

    /**
     * Pixel value for containers width.
     */
    width: PropTypes.string,

    /**
     * Pixel value for containers height.
     */
    height: PropTypes.string,

    // Additional properties.
    isStopped: PropTypes.bool,
    isPaused: PropTypes.bool,
    speed: PropTypes.number,
    segments: PropTypes.arrayOf(PropTypes.number),
    direction: PropTypes.number,
    ariaRole: PropTypes.string,
    ariaLabel: PropTypes.string,
    isClickToPauseDisabled: PropTypes.bool,
    title: PropTypes.string,
    style: PropTypes.string,

};

export default Lottie;
export const propTypes = Lottie.propTypes;
