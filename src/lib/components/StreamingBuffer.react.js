import { useEffect, useState } from "react";
import PropTypes from "prop-types";

/**
 * The Html component makes it possible to render html sanitized via DOMPurify.
 */
const StreamingBuffer = ({url, withCredentials, setProps}) => {
    const [data, setData] = useState("");

    useEffect(() => {
        const sse = new EventSource(url, { withCredentials: withCredentials });
        
        function parseMessage(e) {
          // Handle end of stream.
          if(e.data === "[DONE]"){
            setProps({ done: true })
            sse.close();
            return;
          }
          // Update value.
          setData(data => data.concat(e.data))
        }
      
        sse.onmessage = e => parseMessage(e);
        // Close on error.
        sse.onerror = (e) => {
          console.log(e);
          sse.close();
        }
        // Close on unmount.
        return () => {
          sse.close();
        };
      }, [url]);

    // Update value.
    setProps({ value: data })
    // Don't render anything.
    return <></>;
}

StreamingBuffer.propTypes = {

    /**
     * The ID used to identify this component in Dash callbacks.
     */
    id: PropTypes.string,

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

    /**
    * The data value (streamed).
    */
    value: PropTypes.string,

    /**
    * A boolean indicating if the stream has ended.
    */
    done: PropTypes.bool

};


export default StreamingBuffer
