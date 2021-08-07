import React, {Component} from 'react';
import * as rbm from 'react-burger-menu';
import {defaultProps, propTypes} from "../components/Burger.react";

/**
 * A light wrapper of BurgerMenu.
 */
export default class Burger extends Component {

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

Burger.defaultProps = defaultProps;
Burger.propTypes = propTypes;