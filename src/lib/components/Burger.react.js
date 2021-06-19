import React, {Component} from 'react';
import PropTypes from 'prop-types';
import * as rbm from 'react-burger-menu';

/**
 * A light wrapper of BurgerMenu.
 */
export default class BurgerMenu extends Component {

    constructor(props) {
        super(props);
    }

    render() {
        const {width, height, pageWrapId, outerContainerId, right, disableCloseOnEsc, noOverlay, disableOverlayClick,
            noTransition, customBurgerIcon, customCrossIcon, disableAutoFocus, style, id, className, effect, children}
            = this.props;
        const props = {
            width: width, height: height, pageWrapId: pageWrapId, outerContainerId: outerContainerId, right: right,
            disableCloseOnEsc: disableCloseOnEsc, noOverlay: noOverlay, disableOverlayClick: disableOverlayClick,
            noTransition: noTransition, customBurgerIcon: customBurgerIcon, customCrossIcon: customCrossIcon,
            disableAutoFocus: disableAutoFocus, style: style, id:id, className: className}
        const Menu = rbm.default[effect]
        return (
            <Menu {...props}>
                {children}
            </Menu>
        );
    }

}

BurgerMenu.defaultProps = {
    width: "300px",
    height: "100%",
    effect: "slide"
};

BurgerMenu.propTypes = {

    width: PropTypes.string,

    height: PropTypes.string,

    effect: PropTypes.oneOf(["slide", "stack", "elastic", "bubble", "push", "pushRotate", "scaleDown",
        "scaleRotate", "fallDown", "reveal"]),

    pageWrapId: PropTypes.string,

    outerContainerId: PropTypes.string,

    right: PropTypes.bool,

    disableCloseOnEsc: PropTypes.bool,

    noOverlay: PropTypes.bool,

    disableOverlayClick: PropTypes.bool,

    noTransition: PropTypes.bool,

    customBurgerIcon: PropTypes.bool,

    customCrossIcon: PropTypes.bool,

    disableAutoFocus: PropTypes.bool,

    style: PropTypes.object,

    // State props.

    isOpen: PropTypes.bool,

    // Dash props.

    /**
     * The ID used to identify this component in Dash callbacks
     */
    id: PropTypes.string,

    /**
     * The children of this component
     */
    children: PropTypes.node,

    /**
     * The class of the component
     */
    className: PropTypes.string,

};