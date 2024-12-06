import React from 'react';
import PropTypes from 'prop-types';

/**
 * Used to delay import of js resources until after React had been loaded. Typically used to apply js to dynamic
 * content. Based on https://github.com/Grasia/grasia-dash-components/blob/master/src/components/Import.react.js
 */
export default class DeferScript extends React.Component {

  componentDidMount () {
    const { src, id } = this.props;
    if (src) {
      const {src} = this.props;
      const script = document.createElement('script');

      script.src = src;
      script.defer = true;

      if (id) {
        script.id = id;
      }

      document.body.appendChild(script);
      }
    }

  render() {
    return null;
  }
}

DeferScript.propTypes = {

  /**
  * The ID used to identify this component in Dash callbacks
  */
  id: PropTypes.string,

  /**
  * Local or external source of the javascript to import
  */
  src: PropTypes.string

};
