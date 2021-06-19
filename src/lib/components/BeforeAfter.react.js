import React, {Component} from 'react';
import PropTypes from 'prop-types';
import BeforeAfterSlider from 'react-before-after-slider';

/**
 * A light wrapper of BeforeAfterSlider.
 */
export default class BeforeAfter extends Component {

    render() {
        return (
            <BeforeAfterSlider {...this.props}/>
        );
    }

}

BeforeAfter.propTypes = {

    before: PropTypes.string,

    after: PropTypes.string,

    width: PropTypes.number,

    height: PropTypes.number,

    defaultProgress: PropTypes.number,

    beforeClassName: PropTypes.string,

    afterClassName: PropTypes.string,

    beforeProps: PropTypes.object,

    afterProps: PropTypes.object,

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