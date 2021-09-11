import React, {Component} from 'react';
import PropTypes from 'prop-types';
import {resolveProp} from 'dash-extensions'

/**
 * The EventListener component listens for events from the document object or children if provided.
 */
export default class Transform extends Component {

    constructor(props) {
        super(props);
        this.myRef = React.createRef();  // create reference to enable looping children later
//        this.eventHandler = this.eventHandler.bind(this);
//        this.getSources = this.getSources.bind(this);
    }

//    getSources(){
//        const sources = [...this.myRef.current.children];
//        if(sources.length == 0){
//            sources.push(document);  // if no children are provided, attach to the document object.
//        }
//        return sources;
//    }
//
//    eventHandler(e) {
//        if(this.props.logging){
//            console.log(e);
//        }
//        const eventProps = this.props.events.filter(o => o["event"] === e.type).map(o => o["props"]? o["props"] : [])[0];
//        const eventData = eventProps.reduce(function(o, k) { o[k] = e[k]; return o; }, {});
//        eventData.id = e.srcElement.id;
//        this.props.setProps({n_events: this.props.n_events + 1});
//        this.props.setProps({event: eventData});
//    }
//
//    componentDidMount() {
//        const target = [...this.myRef.current.children];
//        this.getSources().forEach(s => events.forEach(e => s.addEventListener(e, this.eventHandler, false)));
//    }
//
//    componentWillUnmount() {
//        const events = this.props.events.map(o => o["event"]);
//        this.getSources().forEach(s => events.forEach(e => s.removeEventListener(e, this.eventHandler, false)));
//    }

    componentDidUpdate(prevProps) {
      if (prevProps.data !== this.props.data) {
        const target = [...this.myRef.current.children];
        const transform = resolveProp(this.props.transform, this);
        transform(target, this.props.data);
      }
    }

    render() {
        return <div className={this.props.className} style={this.props.style} ref={this.myRef}>
                    {this.props.children}
               </div>;
    }
};

Transform.propTypes = {
    /**
     * The ID used to identify this component in Dash callbacks.
     */
    id: PropTypes.string,

    /**
     * Style function applied on hover.
     */
    transform: PropTypes.oneOfType([PropTypes.string, PropTypes.object]),

    /**
     * The children of this component. If any children are provided, the component will listen for events from these
     components. If no children are specified, the component will listen for events from the document object.
     */
    children: PropTypes.node,

    /**
     * The CSS style of the component.
     */
    style: PropTypes.object,

    /**
     * A custom class name.
     */
    className: PropTypes.string,

    /**
     * Dash-assigned callback that should be called to report property changes
     * to Dash, to make them available for callbacks.
     */
    setProps: PropTypes.func,

    /**
     * Input data for transform.
     */
    data: PropTypes.oneOfType([PropTypes.string, PropTypes.object])

};
