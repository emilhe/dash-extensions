import React from 'react';
import PropTypes from 'prop-types';

/** Simple data store that automatically copies the current value of the sourceData property into destinationData property. Can be used to break circular dependencies. */
export default class ForwardStore extends React.Component {
  componentDidUpdate() {
    if (this.props.hasOwnProperty('sourceData'))
      this.props.setProps({destinationData: this.props.sourceData});
  }

  render() {
    return null;
  }
}

ForwardStore.defaultProps = {
};

ForwardStore.propTypes = {
  /**
  * The ID used to identify this component in Dash callbacks.
  */
  id: PropTypes.string,

  /**
  * Shoud be used to set the new value of the forwarded data.
  */
  sourceData: PropTypes.any,

  /**
  * Shoud be used to read the forwarded value.
  */
  destinationData: PropTypes.any,

  /**
  * Dash-assigned callback that should be called to report property changes
  * to Dash, to make them available for callbacks.
  */
  setProps: PropTypes.func

};