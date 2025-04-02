import { useEffect } from 'react';
import { DashComponentProps } from '../props';

export type Props = DashComponentProps & {
  /**
   * Set this property to value to be forwarded from.
   */
  src?: any;
  /**
   * Read the forwarded value from this property.
   */
  dst?: any;
}

/** 
 * Simple data store that automatically copies the current value of the src property into dst property. Can be used to break circular dependencies. 
 * */
const CycleBreaker = ({src, setProps}: Props) => {
  useEffect(() => {
    if (setProps) {
      setProps({ dst: src });
    }
  }, [src, setProps]);

  return null;
};

export default CycleBreaker;