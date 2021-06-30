import React, {Component} from 'react';
import PropTypes from 'prop-types';
import Mermaid2 from 'react-mermaid2';

/**
 * A light wrapper of https://github.com/e-attestations/react-mermaid2.
 */
export default class Mermaid extends Component {

    render() {
        return (
            <Mermaid2 {...this.props}/>
        );
    }

}

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
     * The children of this component
     */
    children: PropTypes.node,

    /**
     * The class of the component
     */
    className: PropTypes.string,

};