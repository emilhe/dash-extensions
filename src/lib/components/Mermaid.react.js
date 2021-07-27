import React from "react";
import PropTypes from 'prop-types';
import mermaidAPI from "mermaid";

const DEFAULT_CONFIG = {
  startOnLoad: true,
  theme: "forest",
  logLevel: "fatal",
  securityLevel: "strict",
  arrowMarkerAbsolute: false,
  flowchart: {
    htmlLabels: true,
    curve: "linear",
  },
  sequence: {
    diagramMarginX: 50,
    diagramMarginY: 10,
    actorMargin: 50,
    width: 150,
    height: 65,
    boxMargin: 10,
    boxTextMargin: 5,
    noteMargin: 10,
    messageMargin: 35,
    mirrorActors: true,
    bottomMarginAdj: 1,
    useMaxWidth: true,
    rightAngles: false,
    showSequenceNumbers: false,
  },
  gantt: {
    titleTopMargin: 25,
    barHeight: 20,
    barGap: 4,
    topPadding: 50,
    leftPadding: 75,
    gridLineStartPadding: 35,
    fontSize: 11,
    fontFamily: '"Open-Sans", "sans-serif"',
    numberSectionStyles: 4,
    axisFormat: "%Y-%m-%d",
  },
}

const Mermaid = ({chart, config, name, className}) => {
    mermaidAPI.initialize({...DEFAULT_CONFIG, ...config})
    if (!chart) {
        return null
    }
    return <div className={className} dangerouslySetInnerHTML={{__html: mermaidAPI.render(name, chart)}}/>;
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
     * The class of the component
     */
    className: PropTypes.string,

};

export default Mermaid