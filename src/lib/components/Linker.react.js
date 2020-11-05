import React, {Component} from 'react';
import PropTypes from 'prop-types';


/**
 * The Sync component makes it possible to synchronize states between components.
 */
export default class Linker extends Component {

    constructor(props) {
        // Setup meta props.
        const linkValues = [];
        for (let i = 0; i < props.links.length; i++) {
            linkValues.push(true);
        }
        // Call super.
        super(props);
        // Bind meta prop map.
        this.linkValues = linkValues;
    }

    // TODO: The current implementation is NOT efficient.
    _loop_links(apply) {
        for (let i = 0; i < this.props.links.length; i++) {
            const link = this.props.links[i];
            // Loop link elements.
            for (let j = 0; j < link.length; j++) {
                const element = link[j];
                this._loop_children(this.props.children,
                    (child, child_props) => {
                        if (child_props.id === element.id) {
                            apply(i, this.linkValues, element, child, child_props)
                        }
                    })
            }
        }
    }

    _loop_children(children, apply) {
        // If there are no children, stop the recursion.
        if (!children || typeof children !== "object"){
            return
        }
        // If only a single child, convert to list.
        const children_list = "length" in children ? children : [children]
        // Loop the children.
        for (let k = 0; k < children_list.length; k++) {
            const child = children_list[k];
            // If the children has not props, move to the next one.
            if(!("props" in child)){
                continue
            }
            // Do the operation.
            const child_props = child.props._dashprivate_layout? child.props._dashprivate_layout.props : child.props;
            apply(child, child_props)
            // If the child has children, do recursion.
            if("children" in child_props){
                this._loop_children(child_props.children, apply)
            }
        }
    }

    render() {
        const oldLinkValues = this.linkValues.slice();

        function getValue(i, linkValues, element, child, child_props) {
            if (element.prop in child_props && oldLinkValues[i] !== child_props[element.prop]) {
                linkValues[i] = child_props[element.prop];
            }
        }

        function setValue(i, linkValues, element, child, child_props) {
            const currentValue = child_props[element.prop];
            if (linkValues[i] !== currentValue) {
                child_props[element.prop] = linkValues[i];
                child.key = linkValues[i];
            }
        }

        this._loop_links(getValue);
        this._loop_links(setValue);

        return <div className={this.props.className} style={this.props.style}>{this.props.children}</div>
    }

};

Linker.defaultProps = {};
Linker.propTypes = {

    /**
     * List of links. Each link is a list of dicts that specify which properties to synchronize.
     */
    links: PropTypes.arrayOf(
        PropTypes.arrayOf(
                PropTypes.shape({
                    id: PropTypes.string.isRequired,
                    prop: PropTypes.any.isRequired,
                })
        )
    ),

    /**
     * The ID used to identify this component in Dash callbacks.
     */
    id: PropTypes.string,

    /**
     * Dash-assigned callback that should be called to report property changes
     * to Dash, to make them available for callbacks.
     */
    setProps: PropTypes.func,

    /**
     * The children of this component. Must be a list of components with length > 1.
     */
    children: PropTypes.arrayOf(PropTypes.node),

    /**
     * The CSS style of the component.
     */
    style: PropTypes.object,

    /**
     * A custom class name.
     */
    className: PropTypes.string,

};