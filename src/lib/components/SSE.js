import PropTypes from "prop-types";
import { useEffect, useState } from "react";
import { SSE as SSEjs } from "sse.js";


/**
 * The SSE component makes it possible to collect data from e.g. a ResponseStream. It's a wrapper around the SSE.js library.
 * https://github.com/mpetazzoni/sse.js
 */
const SSE = ({ url, options, concat, animate_delay, animate_chunk, setProps }) => {
  const [data, setData] = useState("");
  const [animateData, setAnimateData] = useState("");
  const animate = animate_delay > 0 && animate_chunk > 0;

  useEffect(() => {
    console.log("INIT")
    // Reset on url change.
    setProps({ done: false })
    setData("")
    // Don't do anything if url is not set.
    if (!url) { return () => { }; }
    // Instantiate EventSource.
    const sse = new SSEjs(url, options);
    // Handle messages.
    sse.onmessage = e => {
      // Handle end of stream.
      if (e.data === "[DONE]") {
        console.log("DONE")
        setProps({ done: true })
        sse.close();
        return;
      }
      // Update value.
      setData(data => concat ? data.concat(e.data) : e.data)
    }
    // Close on error.
    sse.onerror = (e) => {
      console.log("ERROR");
      console.log(e);
      sse.close();
    }
    // Close on unmount.
    return () => {
      sse.close();
    };
  }, [url, options]);

  // Animate data.
  useEffect(() => {
    if (!animate) { return () => { }; };
    let buffer = "";
    const interval = setInterval(() => {
      if (buffer.length >= data.length) {
        clearInterval(interval);
      }
      else {
        const endIdx = Math.min(buffer.length + animate_chunk, data.length);
        buffer = data.slice(animateData.length, endIdx);
        setAnimateData(buffer);
      }
    }, animate_delay);
    return () => clearInterval(interval);
  }, [data]);

  // Update value.
  setProps({ value: animate ? animateData : data });

  // Don't render anything.
  return <></>;
}

SSE.defaultProps = {
  concat: true,
  animate_delay: 0,
  animate_chunk: 1,
};

SSE.propTypes = {

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
   * Options passed to the SSE constructor. https://github.com/mpetazzoni/sse.js?tab=readme-ov-file#options-reference
   */
  options: PropTypes.shape({
    headers: PropTypes.object,
    method: PropTypes.string,
    payload: PropTypes.object,
    withCredentials: PropTypes.bool,
    start: PropTypes.bool,
    debug: PropTypes.bool,
  }),

  /**
   * URL of the endpoint.
   */
  url: PropTypes.string,

  /**
  * A boolean indicating if the stream values should be concatenated.
  */
  concat: PropTypes.bool,

  /**
  * The data value. Either the latest, or the concatenated depending on the `concat` property.
  */
  value: PropTypes.string,

  /**
  * If set, each character is delayed by some amount of time. Used to animate the stream.
  */
  animate_delay: PropTypes.number,

  /**
  * Chunk size (i.e. number of characters) for the animation.
  */
  animate_chunk: PropTypes.number,

  /**
  * A boolean indicating if the (current) stream has ended.
  */
  done: PropTypes.bool

};


export default SSE
