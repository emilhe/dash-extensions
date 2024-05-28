import { useEffect, useRef } from "react";
import PropTypes from 'prop-types';

/**
 * The Loading component makes it possible to stop event propagation during loading.
 */

const Loading = (props) => {
    const {
        children,
        loading_state,
        preventDefault
      } = props;
    const container = useRef();

    useEffect(() => {
        const mounted = container && container.current;
        const handlePreventDefault = (e) => {
            e.preventDefault();
        }
        if(mounted){
            const ref = container.current;
            const loading = loading_state && loading_state.is_loading;
            if(!loading){
                preventDefault.forEach(event => {ref.removeEventListener(event, handlePreventDefault, true);})
            }
            else{
                preventDefault.forEach(event => {ref.addEventListener(event, handlePreventDefault, true);})
            }
        }
        return () => {
            const mounted = container && container.current;
            if(mounted){
                const ref = container.current;
                preventDefault.forEach(event => {ref.removeEventListener(event, handlePreventDefault, true);})
            }
        };
    }, [loading_state]);

    return (
        <div ref={container}>
          {children}
        </div>
      );
};

Loading._dashprivate_isLoadingComponent = true;

Loading.defaultProps = {
    preventDefault: ["keydown"],
};

Loading.propTypes = {
    /**
     * The ID of this component, used to identify dash components
     * in callbacks. The ID needs to be unique across all of the
     * components in an app.
     */
    id: PropTypes.string,

    /**
     * Events for which to call preventDefault() during loading.
     */
    preventDefault: PropTypes.arrayOf(PropTypes.string),

    /**
     * Array that holds components to render
     */
    children: PropTypes.oneOfType([
        PropTypes.arrayOf(PropTypes.node),
        PropTypes.node,
    ]),

    /**
     * Object that holds the loading state object coming from dash-renderer
     */
    loading_state: PropTypes.shape({
        /**
         * Determines if the component is loading or not
         */
        is_loading: PropTypes.bool,
        /**
         * Holds which property is loading
         */
        prop_name: PropTypes.string,
        /**
         * Holds the name of the component that is loading
         */
        component_name: PropTypes.string,
    }),
};

export default Loading;
