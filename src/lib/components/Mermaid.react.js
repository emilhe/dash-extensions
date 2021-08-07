import React, {Suspense} from "react";
import PropTypes from 'prop-types';

const LazyMermaid = React.lazy(() => import(/* webpackChunkName: "mermaid" */ '../fragments/Mermaid.react'));

const Mermaid = (props) => {
  return (
    <div>
      <Suspense fallback={<div>Loading...</div>}>
        <LazyMermaid {...props} />
      </Suspense>
    </div>
  );
}

const makeId = (length) => {
    let result = '';
    const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    const charactersLength = characters.length;
    for (let i = 0; i < length; i++) {
        result += characters.charAt(Math.floor(Math.random() * charactersLength));
    }
    return result;
}

Mermaid.defaultProps = {
    name: makeId(5)
};

Mermaid.propTypes = {

    /**
     * The mermaid code of your chart. Check Mermaid js documentation for details
     */
    chart: PropTypes.string,

    /**
     * On optional name of your mermaid diagram/flowchart/gantt etc.
     */
    name: PropTypes.string,

    /**
     * On optional object with one of several Mermaid config parameters. Check Mermaid js documentation for details
     */
    config: PropTypes.object,

    // Dash props.

    /**
     * The ID used to identify this component in Dash callbacks
     */
    id: PropTypes.string,

    /**
     * The class of the component
     */
    className: PropTypes.string,

};

export default Mermaid
export const propTypes = Mermaid.propTypes;
export const defaultProps = Mermaid.defaultProps;
