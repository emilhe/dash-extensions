import React, {Fragment, useEffect, useState} from "react";
import PropTypes from "prop-types";

/**
 * The PropOperator makes it possible to perform various operations on objects.
 */
const ListOperator = ({children}) => {
    const myRef = React.createRef()

    useEffect(() => {
        console.log(children)
    });

    return <Fragment ref={myRef}>{children}</Fragment>;
}

ListOperator.propTypes = {

    /**
     * Apply an operation.
     */
    apply: PropTypes.shape({
        id: PropTypes.string.isRequired,
        operation: PropTypes.oneOf(["append", "clear"]).isRequired,
        value: PropTypes.any,
    }),

    /**
     * List applied operations (just the ids).
     */
    history: PropTypes.arrayOf(PropTypes.string),

    /**
     * Property that this list operator binds to.
     */
    prop: PropTypes.string,

    // Dash props.

    /**
     * The ID used to identify this component in Dash callbacks
     */
    id: PropTypes.string,

    /**
     * The children of this component
     */
    children: PropTypes.node,

};


export default ListOperator
