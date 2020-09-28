import React, {Component} from 'react';
import PropTypes from 'prop-types';

/**
 * The Keyboard component listens for keyboard events.
 */
export default class Keyboard extends Component {

    constructor(props) {
        super(props);
        this.keydownHandler = this.keydownHandler.bind(this);
    }

    keydownHandler(event) {
        if(!this.props.captureKeys || this.props.captureKeys.indexOf(event.key) > -1){
            this.props.setProps({keydown: this.props.eventProps.reduce(
                function(o, k) { o[k] = event[k]; return o; }, {})})
            this.props.setProps({n_keydowns: this.props.n_keydowns + 1})
        }
    }

    componentDidMount() {
        document.addEventListener("keydown", this.keydownHandler, false);
    }

    componentWillUnmount() {
        document.removeEventListener("keydown", this.keydownHandler, false);
    }

    render() {
        return (null);
    }
};

Keyboard.defaultProps = {
    eventProps: ["key", "altKey", "ctrlKey", "shiftKey","metaKey", "repeat"],
    n_keydowns: 0
};


Keyboard.propTypes = {
    /**
     * The ID used to identify this component in Dash callbacks.
     */
    id: PropTypes.string,

    /**
     * The event properties to forward to dash, see https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent.
     */
    eventProps: PropTypes.arrayOf(PropTypes.string),

    /**
     * The keys to capture. Defaults to all keys.
     */
    captureKeys: PropTypes.arrayOf(PropTypes.string),

    /**
     * Dash-assigned callback that should be called to report property changes
     * to Dash, to make them available for callbacks.
     */
    setProps: PropTypes.func,

     /**
     * keydown (dict) the object that holds the result of the key down event. It is a dictionary with the following keys:
     *      "key", "altKey", "ctrlKey", "shiftKey","metaKey", "repeat". Those keys have the following values:
     *
     *    - key (str) which key is pressed
     *    - altKey (bool) whether the Alt key is pressed
     *    - ctrlKey (bool) Ctrl key is pressed
     *    - shiftKey (bool) Shift key is pressed
     *    - metaKey (bool) Meta key is pressed (Mac: Command key or PC: Windows key)
     *    - repeat (bool) whether the key is held down
     */
    keydown: PropTypes.object,

     /**
     * A counter, which is incremented on each key down event, similar to n_clicks for buttons.
     */
    n_keydowns: PropTypes.number

};
