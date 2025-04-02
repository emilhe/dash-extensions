import React from "react";
import DOMPurify from "dompurify";
import { Props } from '../components/Purify'; // reuse the interface

const Purify = ({ html = "", config, className }: Props) => {
  const html_safe = DOMPurify.sanitize(html, config);
  return <div className={className} dangerouslySetInnerHTML={{ __html: html_safe }} />;
};

export default Purify;
