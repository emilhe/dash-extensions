import { useEffect } from 'react';
import { DashComponentProps } from '../props';

export type Props = DashComponentProps & {
  /**
   * Local or external source of the javascript to import.
   */
  src?: string;
};

/**
 * Used to delay import of js resources until after React had been loaded. Typically used to apply js to dynamic content.
 */
const DeferScript = ({ id, src }: Props) => {
  useEffect(() => {
    if (src) {
      const script = document.createElement('script');
      script.src = src;
      script.defer = true;
      if (id) {
        script.id = id;
      }
      document.body.appendChild(script);
    }
  }, [src, id]);

  return null;
};

export default DeferScript;
