import React, {Component} from 'react';
import PropTypes from 'prop-types';

import L from 'react-lottie';

/**
 * Light wrapper of the react Lottie component for Dash.
 */
export default class Lottie extends Component {
    render() {
        // Get data from url.
        if (this.props.url) {
            var Httpreq = new XMLHttpRequest();
            Httpreq.open("GET", this.props.url, false);
            Httpreq.send(null);
            this.props.options.animationData = JSON.parse(Httpreq.responseText);
        }
        // TODO: Add eventListeners (see https://www.npmjs.com/package/react-lottie)
        return <L {...this.props}/>
    }
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

