import {Component} from 'react';
import PropTypes from 'prop-types';
import {toByteArray} from 'base64-js';

/**
 * The Download component opens a download dialog when the data property (dict of filename, content, and type) changes.
 */
export default class Download extends Component {

    componentDidUpdate(prevProps) {
        const {data} = this.props;
        if(data && data !== prevProps.data){
            const mime_type = data.mime_type? data.mime_type : this.props.mime_type;
            const base64 = data.base64? data.base64 : this.props.base64;
            const content = base64? toByteArray(data.content) : data.content;
            // Construct the blob.
            const blob = new Blob([content], {type: mime_type});
            const filename = data.filename;
            // Save file function, from https://stackoverflow.com/questions/19327749/javascript-blob-filename-without-link
            if (window.navigator.msSaveOrOpenBlob) {
                window.navigator.msSaveOrOpenBlob(blob, filename);
            } else {
                const a = document.createElement('a');
                document.body.appendChild(a);
                const url = window.URL.createObjectURL(blob);
                a.href = url;
                a.download = filename;
                a.click();
                setTimeout(() => {
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                }, 0);
            }
        }
    }

    render() {
        return null;
    }
}

Download.defaultProps = {
    mime_type: "text/plain",
    base64: false,
};

Download.propTypes = {
    /**
     * The ID used to identify this component in Dash callbacks.
     */
    id: PropTypes.string,

    /**
     * When set, a download is invoked using a Blob.
     */
    data: PropTypes.shape({
        filename: PropTypes.string.isRequired,
        content: PropTypes.any.isRequired,
        base64: PropTypes.bool,
        mime_type: PropTypes.string,
    }),

    /**
     * Default value for base64.
     */
    base64: PropTypes.bool,

    /**
     * Default value for mime_type.
     */
    mime_type: PropTypes.string,

    /**
     * Dash-assigned callback that should be called to report property changes
     * to Dash, to make them available for callbacks.
     */
    setProps: PropTypes.func
};
