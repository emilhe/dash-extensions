import React, {Suspense} from 'react';
import PropTypes from 'prop-types';

const LazyBurger = React.lazy(() => import(/* webpackChunkName: "burger" */ '../fragments/BurgerMenu.react'));

const BurgerMenu = (props) => {
  return (
    <div>
      <Suspense fallback={<div>Loading...</div>}>
        <LazyBurger {...props} />
      </Suspense>
    </div>
  );
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

export default BurgerMenu;
export const propTypes = BurgerMenu.propTypes;
export const defaultProps = BurgerMenu.defaultProps;
