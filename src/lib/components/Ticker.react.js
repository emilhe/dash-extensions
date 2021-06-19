import React, {Component} from 'react';
import PropTypes from 'prop-types';
import ReactTicker from 'react-ticker';

/**
 * A light wrapper of ReactTicker.
 */
export default class Ticker extends Component {

    render() {
        return (
            <ReactTicker {...this.props}>
                {({index}) => (
                    <>
                        {this.props.children}
                    </>
                )}
            </ReactTicker>
        );
    }

}

Ticker.propTypes = {

    direction: PropTypes.oneOf(["toRight", "toLeft"]),

    mode: PropTypes.oneOf(["chain", "await", "smooth"]),

    move: PropTypes.bool,

    offset: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),

    speed: PropTypes.number,

    height: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),

    // Dash props.

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

};