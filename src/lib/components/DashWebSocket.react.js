import React, {Component} from 'react';
import PropTypes from 'prop-types';

/**
 * A simple interface to
 */
export default class DashWebSocket extends Component {

    _init_client() {
        // Create a new client.
        let {url} = this.props;
        const {protocols} = this.props;
        url = url? url : "ws://" + location.host + "/ws";
        this.client = new WebSocket(url, protocols);
        // Listen for events.
        this.client.onopen = (e) => {
            // TODO: Add more properties here?
            this.props.setProps({
                open: {
                    isTrusted: e.isTrusted,
                    origin: e.origin,
                    timeStamp: e.timeStamp
                }
            })
        }
        this.client.onmessage = (e) => {
            // TODO: Add more properties here?
            this.props.setProps({
                message: {
                    data: e.data,
                    isTrusted: e.isTrusted,
                    origin: e.origin,
                    timeStamp: e.timeStamp
                }
            })
        }
        this.client.onerror = (e) => {
            // TODO: Implement this one also.
            this.props.setProps({error: JSON.stringify(e)})
        }
        this.client.onclose = (e) => {
            // TODO: Add more properties here?
            this.props.setProps({
                close: {
                    code: e.code,
                    reason: e.reason,
                    wasClean: e.wasClean,
                    isTrusted: e.isTrusted,
                    timeStamp: e.timeStamp
                }
            })
        }
    }

    componentDidMount() {
        this._init_client()
    }

    componentDidUpdate(prevProps) {
        const {send} = this.props;
        // Send messages.
        if (send && send !== prevProps.send) {
            if (this.props.open && !this.props.close) {
                this.client.send(send)
            }
        }
        // TODO: Maybe add support for changing the url?
    }

    componentWillUnmount() {
        // Clean up (close the connection).
        this.client.close();
    }

    render() {
        return (null);
    }

}

DashWebSocket.propTypes = {

    /**
     * This property is set with the content of the onopen event.
     */
    open: PropTypes.object,

    /**
     * When messages are received, this property is updated with the message content.
     */
    message: PropTypes.object,

    /**
     * This property is set with the content of the onerror event.
     */
    error: PropTypes.object,

    /**
     * This property is set with the content of the onclose event.
     */
    close: PropTypes.object,

    /**
     * When this property is set, a message is sent with its content.
     */
    send: PropTypes.object,

    /**
     * The websocket endpoint (e.g. wss://echo.websocket.org).
     */
    url: PropTypes.string,

    /**
     * Supported websocket protocols (optional).
     */
    protocols: PropTypes.arrayOf(PropTypes.string),

    /**
     * The ID used to identify this component in Dash callbacks.
     */
    id: PropTypes.string,

    /**
     * Dash-assigned callback that should be called to report property changes
     * to Dash, to make them available for callbacks.
     */
    setProps: PropTypes.func

}