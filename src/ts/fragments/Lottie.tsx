import React, { useEffect, useMemo, useRef } from 'react';
import ReactLottie from "lottie-react";
import { Props } from '../components/Lottie';

/**
 * Light wrapper of the react-lottie component for Dash.
 */
const Lottie = ({url, speed=1, action, options}: Props) => {
  const lottieRef = useRef<any>(null);

  // Synchronously fetch animation data if a URL is provided.
  const computedOptions = useMemo(() => {
    const newOptions = { ...options, ...{animationData: undefined}};
    if (url) {
      const xhr = new XMLHttpRequest();
      xhr.open("GET", url, false);
      xhr.send(null);
      if (xhr.status === 200) {
        try {
          newOptions.animationData = JSON.parse(xhr.responseText);
        } catch (error) {
          console.error("Error parsing animation data from url:", error);
        }
      }
    }
    return newOptions;
  }, [url, options]);

  // Effect to update when the speed changes.
  useEffect(() => {
    if (lottieRef.current) {
        lottieRef.current.setSpeed(speed);
    }
  }, [speed]);

  // Effect to update when the play state changes.
  useEffect(() => {
    if (lottieRef.current && action) {
        lottieRef.current[action]();
    }
  }, [action]);

  return <ReactLottie lottieRef={lottieRef} {...computedOptions} />;
};

export default Lottie;
