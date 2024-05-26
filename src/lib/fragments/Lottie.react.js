import React, {Component} from 'react';
import {propTypes} from '../components/Lottie.react';
import L from 'react-lottie';

/**
 * Light wrapper of the react Lottie component for Dash.
 */
export default class Lottie extends Component {

    constructor(props) {
        super(props);
        this.myRef = React.createRef();
        this.el = null;
    }

    componentDidMount() {
        this.el.ref.current.componentDidUpdate();
    }

    shouldComponentUpdate(nextProps){
        // On speed change, don't re-render.
        if(this.props.speed && nextProps.speed !== this.props.speed){
            // Update speed prop of animation.
            const nProps = Object.assign({}, this.el.ref.current.props);
            nProps.speed = nextProps.speed;
            this.el.ref.current.props = nProps;
            // Refresh the animation.
            this.el.ref.current.componentDidUpdate();
            // Don't recreate the animation.
            return false;
        }
        // Do re-render if anything but loading_state has changed.
        for(const prop in nextProps) {
            if(prop === "loading_state"){
                continue;
            }
            if(this.props[prop] !== nextProps[prop]){
                return true;
            }
        }
        // If no prop has changes, don't re-render.
        return false;
    }

    render() {
        // Get data from url.
        if (this.props.url) {
            var Httpreq = new XMLHttpRequest();
            Httpreq.open("GET", this.props.url, false);
            Httpreq.send(null);
            this.props.options.animationData = JSON.parse(Httpreq.responseText);
        }
        // TODO: Add eventListeners (see https://www.npmjs.com/package/react-lottie)
        this.el = <L {...this.props} ref={this.myRef}/>;
        return this.el
    }
}

Lottie.propTypes = propTypes;
