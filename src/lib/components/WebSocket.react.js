import {Component} from 'react';
import PropTypes from 'prop-types';

/**
 * A simple interface to
 */
export default class DashWebSocket extends Component {

    _init_client() {
        // Create a new client.
        let {url} = this.props;
        const {protocols} = this.props;
        // No url - client will be created, when url will be updated
        if (!url) {
            return (null)
        }
        this.client = new WebSocket(url, protocols);
        this.props.setProps({
            state: {
                readyState: WebSocket.CONNECTING,
            }
        })
        // Listen for events.
        this.client.onopen = (e) => {
            // TODO: Add more properties here?
            this.props.setProps({
                state: {
                    // Mandatory props.
                    readyState: WebSocket.OPEN,
                    isTrusted: e.isTrusted,
                    timeStamp: e.timeStamp,
                    // Extra props.
                    origin: e.origin,
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
            // TODO: Implement error handling.
            this.props.setProps({error: JSON.stringify(e)})
        }
        this.client.onclose = (e) => {
            // TODO: Add more properties here?
            this.props.setProps({
                state: {
                    // Mandatory props.
                    readyState: WebSocket.CLOSED,
                    isTrusted: e.isTrusted,
                    timeStamp: e.timeStamp,
                    // Extra props.
                    code: e.code,
                    reason: e.reason,
                    wasClean: e.wasClean,
                }
            })
        }
    }

    _destroy_client() {
        // Clean up (close the connection).
        this.client.onopen = null;
        this.client.onclose = null;
        this.client.onerror = null;
        this.client.onmessage = null;
        this.client.close();
        this.client = null;
    }

    componentDidMount() {
        this._init_client();
    }

    async componentDidUpdate(prevProps) {
        // If the url has changed, close the connection and create a new one.
        const {url} = this.props;
        if (url && url !== prevProps.url) {
            if (this.client) {
                this._destroy_client();
            }
            this._init_client();
            // always wait a bit for the connection to be ready
            await new Promise(r => setTimeout(r, 100));
        }
        // If there is no (new) message to send, return.
        const {send} = this.props;
        if (!send || send === prevProps.send) {
            return;
        }
        // If the connection is not open, try to connect.
        if (this.props.state.readyState === WebSocket.CLOSED) {
            console.log('Websocket CLOSED. Attempting to reconnect...');
            if (this.client) {
                this._destroy_client();
            }
            this._init_client();
            // always wait a bit for the connection to be ready
            await new Promise(r => setTimeout(r, 100));
        }
        // If the connection is still not open, wait for a while and try again.
        if (this.props.state.readyState === WebSocket.CONNECTING) {
            console.log('Websocket CONNECTING. Delaying sending message...');
            await new Promise(r => setTimeout(r, this.props.timeout));
        }
        // Wuhu! The connection is open. Send the message.
        if (this.props.state.readyState === WebSocket.OPEN) {
            this.client.send(send);
            return;
        }
        // If we get there, the connection failed.
        console.log('Websocket connection failed. Aborting.');
    }

    componentWillUnmount() {
        this._destroy_client();
    }

    render() {
        return (null);
    }

}

DashWebSocket.defaultProps = {
    state: {readyState: WebSocket.CLOSED},
    timeout: 1000
}

DashWebSocket.propTypes = {

    /**
     * This websocket state (in the readyState prop) and associated information.
     */
    state: PropTypes.oneOfType([PropTypes.object, PropTypes.string]),

    /**
     * When messages are received, this property is updated with the message content.
     */
    message: PropTypes.oneOfType([PropTypes.object, PropTypes.string]),

    /**
     * This property is set with the content of the onerror event.
     */
    error: PropTypes.oneOfType([PropTypes.object, PropTypes.string]),

    /**
     * When this property is set, a message is sent with its content.
     */
    send: PropTypes.oneOfType([PropTypes.object, PropTypes.string]),

    /**
     * The websocket endpoint (e.g. wss://echo.websocket.org).
     */
    url: PropTypes.string,

    /**
     * Supported websocket protocols (optional).
     */
    protocols: PropTypes.arrayOf(PropTypes.string),

    /**
     * How many ms to wait for websocket to be ready when sending a message (optional).
     */
    timeout: PropTypes.number,

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
