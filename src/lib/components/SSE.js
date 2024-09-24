import PropTypes from "prop-types";
import { useEffect, useState } from "react";
import { SSE as SSEjs } from "sse.js";


/**
 * The SSE component makes it possible to collect data from e.g. a ResponseStream. It's a wrapper around the SSE.js library.
 * https://github.com/mpetazzoni/sse.js
 */
const SSE = ({ url, options, concat, animate_delay, animate_chunk, animate_prefix, animate_suffix, setProps, done }) => {
  const [data, setData] = useState("");
  const [animateData, setAnimateData] = useState("");
  const animate = animate_delay > 0 && animate_chunk > 0;

  useEffect(() => {
    // Reset on url change.
    setProps({ done: false })
    setData("")
    setAnimateData("")
    // Don't do anything if url is not set.
    if (!url) { return () => { }; }
    // Instantiate EventSource.
    const sse = new SSEjs(url, options);
    // Handle messages.
    sse.onmessage = e => {
      // Handle end of stream.
      if (e.data === "[DONE]") {
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

  useEffect(() => {
    // Don't animate if not set.
    if (!animate) { return () => { }; };
    // Apply prefix/suffix filters.
    let filteredData = data;
    if (animate_prefix) {
      if (!data.includes(animate_prefix)) {
        return () => { };
      }
      filteredData = filteredData.slice(animate_prefix.length)
    }
    if (filteredData.includes(animate_suffix)) {
      filteredData = filteredData.split(animate_suffix)[0]
    }
    // If done, animate the whole data.
    if (done) {
      setAnimateData(filteredData);
      return () => { };
    };
    // If there is not data, just return.
    if (filteredData.length === 0) {
      return () => { };
    };
    // Animate data.
    let buffer = animateData;
    const interval = setInterval(() => {
      // If we're done, stop the interval.
      if (buffer.length >= filteredData.length) {
        clearInterval(interval);
      }
      // Otherwise, move to the next chunk.
      const endIdx = Math.min(buffer.length + animate_chunk, filteredData.length);
      buffer = filteredData.slice(0, endIdx);
      setAnimateData(buffer);
    }, animate_delay);
    return () => clearInterval(interval);
  }, [data, done]);

  // Update value(s).
  setProps({ animation: animateData });
  setProps({ value: data });

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
    payload: PropTypes.oneOfType([PropTypes.object, PropTypes.string]),
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
  * Prefix to be excluded from the animation.
  */
  animate_prefix: PropTypes.string,

  /**
  * Suffix to be excluded from the animation.
  */
  animate_suffix: PropTypes.string,

  /**
  * The data value. Either the latest, or the concatenated depending on the `concat` property.
  */
  animation: PropTypes.string,

  /**
  * A boolean indicating if the (current) stream has ended.
  */
  done: PropTypes.bool

};


export default SSE
