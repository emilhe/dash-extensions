import React, {Component} from 'react';
import PropTypes from 'prop-types';
import * as rbm from 'react-burger-menu';

/**
 * A modified version of dcc.Link that adds a few more options. E.g. you can disable scrolling to
 * the top upon updating the url.
 */
export default class BurgerMenu extends Component {

    constructor(props) {
        super(props);
    }

    render() {

        const {width, height, className, style, id, children, overlay, position, effect} = this.props;
        const props = {style: style, id:id, className: className, width: width, height: height,
            right: position === "right", noOverlay: !overlay}
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
    overlay: true,
    position: "right",
    effect: "slide"
};

BurgerMenu.propTypes = {

    children: PropTypes.node,

    style: PropTypes.object,

    id: PropTypes.string,

    width: PropTypes.string,

    height: PropTypes.string,

    position: PropTypes.oneOf("left", "right"),

    effect: PropTypes.oneOf("slide", "stack", "elastic", "bubble", "push", "pushRotate", "scaleDown",
        "scaleRotate", "fallDown", "reveal"),

    className: PropTypes.string,

    overlay: PropTypes.bool

};