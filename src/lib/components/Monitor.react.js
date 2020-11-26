import React, {Component} from 'react';
import PropTypes from 'prop-types';


/**
 * The Sync component makes it possible to synchronize states between components.
 */
export default class Monitor extends Component {

    constructor(props) {
        // Call super.
        super(props);
        // For caching of the monitored data.
        this.data = {};
    }

    // region Getting values

    _loop_children_recursively(children, apply) {
        // No children, just return.
        if (!children) {
            return
        }
        // Single child, look at it.
        if (!children.length) {
            this._loop_children_recursively_inner(children, apply);
            return
        }
        // Multiple children, loop them.
        for (let i = 0; i < children.length; i++) {
            this._loop_children_recursively_inner(children[i], apply);
        }
    }

    _loop_children_recursively_inner(child, apply) {
        if (!child.props) {
            return
        }
        apply(child);
        this._loop_children_recursively(child.props.children, apply)
    }

    _monitor(key, props, target) {
        if (!props) {
            return
        }
        const elements = this.props.probes[key];
        for (let i = 0; i < elements.length; i++) {
            const id = elements[i].id ? elements[i].id : elements[i][0]
            const prop = elements[i].prop ? elements[i].prop : elements[i][1]
            // Check if there is a match.
            if (props.id !== id || !(prop in props)) {
                continue
            }
            // Check if value has changed.
            if (this.data[key] && this.data[key].value === props[prop]) {
                continue
            }
            // TODO: Add other properties here? Time maybe?
            target[key] = {value: props[prop], trigger: {id: id, prop: prop}}
        }
    }

    // endregion

    render() {
        // Update data.
        const newData = Object.assign({}, this.data)
        React.Children.map(this.props.children, (child) => {
            for (const key in this.props.probes) {
                const dlp = child.props._dashprivate_layout;
                const children = dlp.props.children;
                this._monitor(key, dlp.props, newData)
                this._loop_children_recursively(children, (child) => this._monitor(key, child.props, newData))
            }
        })
        console.log(this.data)
        // console.log(this.props)
        // console.log(this.props.setProps)
        // const d = new Date();
        this.data = newData;
        this.props.setProps({data: newData})
        // Render as-is.
        return <div className={this.props.className} style={this.props.style}>{this.props.children}</div>
    }

};

Monitor.defaultProps = {
};
Monitor.propTypes = {

    /**
     * List of probes. Each link is a list of dicts that specify which properties each probe records.
     */
    probes: PropTypes.objectOf(
        PropTypes.arrayOf(
            PropTypes.oneOfType([
                // tuple notation, i.e. (id, prop)
                PropTypes.arrayOf(PropTypes.string),
                // object notation, i.e. {"id": id, "prop": prop}
                PropTypes.shape({
                    id: PropTypes.string.isRequired,
                    prop: PropTypes.any.isRequired,
                })
            ])
        ),
    ),

    // TODO: Add structure
    data: PropTypes.object,

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