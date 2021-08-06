import React from "react";
import mermaidAPI from "mermaid";
import DOMPurify from 'dompurify';
import {propTypes, defaultProps} from "../components/Mermaid.react";

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
    const svg_string = mermaidAPI.render(name, chart);
    const svg_string_safe = DOMPurify.sanitize(svg_string, {ADD_TAGS: ['foreignObject']});
    return <div className={className} dangerouslySetInnerHTML={{__html: svg_string_safe}}/>;
}

export default Mermaid

Mermaid.defaultProps = defaultProps;
Mermaid.propTypes = propTypes;
