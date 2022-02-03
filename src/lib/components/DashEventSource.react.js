import React from "react";
import PropTypes from "prop-types";

/** An interface to server sent events in Dash */
export default class DashEventSource extends React.Component {
    componentDidMount() {
        const { url, withCredentials, setProps } = this.props;

        this.eventSource = new EventSource(url, { withCredentials });

        this.eventSource.onopen = () => {
            setProps({ readyState: EventSource.OPEN });
        };

        this.eventSource.onmessage = (event) => {
            setProps({ message: event.data });
        };

        this.eventSource.onerror = (event) => {
            setProps({ error: JSON.stringify(event) });
        };
    }

    componentDidUpdate() {
        const { close } = this.props;
        if (close) {
            this.eventSource.close();
            this.props.setProps({ readyState: EventSource.CLOSED });
        }
    }

    componentWillUnmount() {
        this.eventSource.close();
    }

    render() {
        return null;
    }
}

DashEventSource.propTypes = {
    /**
     * The ID used to identify this component in Dash callbacks.
     */
    id: PropTypes.string,

    /**
     * Close event source
     */
    close: PropTypes.bool,

    /**
     * Error
     */
    error: PropTypes.string,

    /**
     * Received message
     */
    message: PropTypes.string,

    /**
     * A number representing the state of the connection. Possible values are CONNECTING (0), OPEN (1), or CLOSED (2).
     */
    readyState: PropTypes.number,

    /**
     * Dash-assigned callback that should be called to report property changes
     * to Dash, to make them available for callbacks.
     */
    setProps: PropTypes.func,

    /**
     * A boolean value indicating whether the EventSource object was instantiated with cross-origin (CORS) credentials set (true), or not (false, the default).
     */
    withCredentials: PropTypes.bool,

    /**
     * A DOMString representing the URL of the source.
     */
    url: PropTypes.string.isRequired,
};
