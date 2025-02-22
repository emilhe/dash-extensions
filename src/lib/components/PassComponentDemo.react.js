import React from 'react';
import PropTypes from 'prop-types';

/**
 * Demo for passing a component as a prop.
 */
const PassComponentDemo = ({components, className, id}) => {
    const ctx = window.dash_component_api.useDashContext();
    const ExternalWrapper = window.dash_component_api.ExternalWrapper;
    const renderedComponents = components.map((component, index) => {
        return (
            <ExternalWrapper
                componentType={component.type}
                componentNamespace={component.namespace}
                componentPath={[...ctx.componentPath, 'external']}
                {...component.props}
            />
        );
    });
    return (
        <div id={id} className={className}>
            {renderedComponents}
        </div>
    );
};

PassComponentDemo.propTypes = {
    /**
     * Components to render.
     */
    components: React.ReactNode,

    // Dash props.

    /**
     * The ID used to identify this component in Dash callbacks
     */
    id: PropTypes.string,

    /**
     * The class of the component
     */
    className: PropTypes.string,
};

export default PassComponentDemo;
