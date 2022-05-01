import React from 'react';
import PropTypes from 'prop-types';

/** Simple data store that automatically copies the current value of the src property into dst property. Can be used to break circular dependencies. */
export default class CycleBreaker extends React.Component {
  componentDidUpdate() {
    if (this.props.hasOwnProperty('src')){
      this.props.setProps({dst: this.props.src});
    }
  }

  render() {
    return null;
  }
}

CycleBreaker.defaultProps = {
};

CycleBreaker.propTypes = {
  /**
  * The ID used to identify this component in Dash callbacks.
  */
  id: PropTypes.string,

  /**
  * Set this property to value to be forwarded from .
  */
  src: PropTypes.any,

  /**
  * Read the forwarded value from this property.
  */
  dst: PropTypes.any,

  /**
  * Dash-assigned callback that should be called to report property changes
  * to Dash, to make them available for callbacks.
  */
  setProps: PropTypes.func

};