import DOMPurify from "dompurify";
import React from "react";
import PropTypes from "prop-types";

/**
 * The Html component makes it possible to render html sanitized via DOMPurify.
 */
const Purify = ({html, config, className}) => {
    const html_safe = DOMPurify.sanitize(html, config);
    return <div className={className} dangerouslySetInnerHTML={{__html: html_safe}}/>;
}

Purify.propTypes = {

    /**
     * Html string
     */
    html: PropTypes.string,

    /**
     * Configuration (optional) of DOMPurify, see the docs https://github.com/cure53/DOMPurify
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


export default Purify
