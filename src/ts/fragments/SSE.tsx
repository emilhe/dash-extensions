import React, { useEffect, useState } from 'react';
import { SSE as SSEjs, SSEvent } from 'sse.js';
import { Props } from '../components/SSE'; // reuse the interface

const SSE = ({
  url,
  options,
  concat = true,
  animate_delay = 0,
  animate_chunk = 1,
  animate_prefix,
  animate_suffix,
  setProps,
  done,
}: Props) => {
  const [data, setData] = useState<string>('');
  const [animateData, setAnimateData] = useState<string>('');
  const [doneData, setDoneData] = useState<boolean>(done || false);

  const animate = animate_delay > 0 && animate_chunk > 0;

  useEffect(() => {
    // Reset on URL change.
    setDoneData(false);
    setData('');
    setAnimateData('');
    if (!url) {
      return;
    }
    // Instantiate EventSource.
    const sse = new SSEjs(url, options);
    sse.onmessage = (e: SSEvent) => {
      // Handle end of stream.
      if (e.data === '[DONE]') {
        setDoneData(true);
        sse.close();
        return;
      }
      // Update value.
      setData((prev) => (concat ? prev.concat(e.data) : e.data));
    };
    sse.onerror = (e: Event) => {
      console.log('ERROR', e);
      sse.close();
    };
    // Close on unmount.
    return () => {
      sse.close();
    };
  }, [url, options, concat]);

  useEffect(() => {
    if (!animate) {
      return;
    }
    let filteredData = data;
    if (animate_prefix) {
      if (!data.includes(animate_prefix)) {
        return;
      }
      filteredData = filteredData.slice(animate_prefix.length);
    }
    if (animate_suffix && filteredData.includes(animate_suffix)) {
      filteredData = filteredData.split(animate_suffix)[0];
    }
    // If done, animate the whole data.
    if (done) {
      setAnimateData(filteredData);
      return;
    }
    if (filteredData.length === 0) {
      return;
    }
    let buffer = animateData;
    const interval = setInterval(() => {
      if (buffer.length >= filteredData.length) {
        clearInterval(interval);
      }
      const endIdx = Math.min(buffer.length + animate_chunk, filteredData.length);
      buffer = filteredData.slice(0, endIdx);
      setAnimateData(buffer);
    }, animate_delay);
    return () => clearInterval(interval);
  }, [
    data,
    done,
    animate,
    animate_delay,
    animate_chunk,
    animate_prefix,
    animate_suffix,
    animateData,
  ]);

  useEffect(() => {
    if (setProps) {
      setProps({
        animation: animateData,
        value: data,
        done: doneData,
      });
    }
  }, [animateData, data, doneData, setProps]);

  return <></>;
};

export default SSE;
