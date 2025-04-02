import React, { useEffect, useState } from 'react';
import DOMPurify from 'dompurify';
import mermaidAPI, { MermaidConfig } from 'mermaid';
import { Props } from '../components/Mermaid';

export const DEFAULT_CONFIG: MermaidConfig = {
  startOnLoad: true,
  theme: "forest",
  logLevel: 5, // fatal
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
    // fontFamily: '"Open-Sans", "sans-serif"',
    numberSectionStyles: 4,
    axisFormat: "%Y-%m-%d",
  },
};

const makeId = (length: number): string => {
  let result = '';
  const characters =
    'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  const charactersLength = characters.length;
  for (let i = 0; i < length; i++) {
    result += characters.charAt(Math.floor(Math.random() * charactersLength));
  }
  return result;
};

const Mermaid: React.FC<Props> = ({ chart, config, name, className }) => {
  const [svg, setSvg] = useState<string>('');
  const diagName = name || makeId(5);

  useEffect(() => {
    mermaidAPI.initialize({ ...DEFAULT_CONFIG, ...config });
    if (chart) {
      mermaidAPI.render(diagName, chart).then(({ svg }) => {
        setSvg(DOMPurify.sanitize(svg, { ADD_TAGS: ['foreignObject'] }));
      });
    }
  }, [chart, config, diagName]);

  if (!chart) {
    return null;
  }

  return (
    <div className={className} dangerouslySetInnerHTML={{ __html: svg }} />
  );
};

Mermaid.defaultProps = {
  name: makeId(5),
};

export default Mermaid;
