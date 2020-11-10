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

    render() {
        const oldLinkValues = this.linkValues.slice();

        // Getting.
        this.props.links.map((link, i) => {
            for (let j = 0; j < link.length; j++) {
                const element = link[j];
                React.Children.map(this.props.children, (child) => {
                    const child_props = child.props._dashprivate_layout? child.props._dashprivate_layout.props : child.props;
                    if (element.prop in child_props && oldLinkValues[i] !== child_props[element.prop]) {
                        this.linkValues[i] = child_props[element.prop];
                    }
                })
            }
        });

        // Setting.
        const children = React.Children.map(this.props.children, (child) => {
            const child_props = child.props._dashprivate_layout? child.props._dashprivate_layout.props : child.props;
            const newProps = {};
            // Figure out which props changed.
            this.props.links.map((link, i) => {
                for (let j = 0; j < link.length; j++) {
                    const element = link[j];
                    const currentValue = child_props[element.prop];
                    if (this.linkValues[i] !== currentValue) {
                        newProps[element.prop] = this.linkValues[i];
                    }
                }
            });
            // Return early if there was no change.
            if(newProps.length < 1){
                return child;
            }
            // Otherwise, modify the child.
            const dlp = Object.assign({}, child.props._dashprivate_layout);
            dlp.props = Object.assign(dlp.props, newProps);
            return React.cloneElement(child, {_dashprivate_layout: dlp}, child.children);
        });

        return <div className={this.props.className} style={this.props.style}>{children}</div>
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