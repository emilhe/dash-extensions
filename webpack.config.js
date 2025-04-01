const path = require('path');
const webpack = require('webpack');
const packagejson = require('./package.json');
const NodePolyfillPlugin = require("node-polyfill-webpack-plugin");
const WebpackDashDynamicImport = require('@plotly/webpack-dash-dynamic-import');

const dashLibraryName = packagejson.name.replace(/-/g, '_');

module.exports = (env, argv) => {

    let mode;

    const overrides = module.exports || {};

    // if user specified mode flag take that value
    if (argv && argv.mode) {
        mode = argv.mode;
    }

    // else if configuration object is already set (module.exports) use that value
    else if (overrides.mode) {
        mode = overrides.mode;
    }

    // else take webpack default (production)
    else {
        mode = 'production';
    }

    let filename = (overrides.output || {}).filename;
    if(!filename) {
        const modeSuffix = mode === 'development' ? '.dev' : '';
        filename = `${dashLibraryName}${modeSuffix}.js`;
    }

    const entry = overrides.entry || {main: './src/lib/index.js'};

    const devtool = overrides.devtool || 'source-map';

    const externals = ('externals' in overrides) ? overrides.externals : ({
        react: 'React',
        'react-dom': 'ReactDOM',
        'plotly.js': 'Plotly',
        'prop-types': 'PropTypes',
    });

    return {
        mode,
        entry,
        output: {
            path: path.resolve(__dirname, dashLibraryName),
            chunkFilename: '[name].js',
            filename,
            library: dashLibraryName,
            libraryTarget: 'window',
        },
        devtool,
        externals,
        resolve: {
            fallback: {
              assert: false,
              // You can disable others if needed
            },
        },
        module: {
            rules: [
                {
                    test: /\.jsx?$/,
                    exclude: /node_modules/,
                    use: {
                        loader: 'babel-loader',
                    },
                },
                {
                    test: /\.css$/,
                    use: [
                        {
                            loader: 'style-loader',
                            options: {
                                insertAt: 'top'
                            }
                        },
                        {
                            loader: 'css-loader',
                        },
                    ],
                },
            ],
        },
        optimization: {
            splitChunks: {
                cacheGroups: {
                    shared: {
                        priority: 5,
                        chunks: 'all',
                        minSize: 0,
                        minChunks: 2,
                        name: 'dash_core_components-shared'
                    },
                    async: {
                        chunks: 'async',
                        minSize: 0,
                        name(module, chunks, cacheGroupKey) {
                            return `${cacheGroupKey}-${chunks[0].name}`;
                        },
                        priority: 1,
                    },
                    mermaid: {
                        test: /[\\/]node_modules[\\/](mermaid|@braintree\/sanitize-url|cytoscape|cytoscape-cose-bilkent|cytoscape-fcose|d3|dagre-d3-es|dayjs|elkjs|khroma|lodash-es|non-layered-tidy-tree-layout|stylis|ts-dedent|uuid|web-worker|cose-base|layout-base)[\\/]/,
                        name: 'async-mermaid',
                        chunks: 'all',
                        priority: 10,
                        enforce: true,  // We FORCE all mermaid content into this chunk
                        reuseExistingChunk: true
                    }
                }
            }
        },
        plugins: [
            new WebpackDashDynamicImport(),
            new webpack.SourceMapDevToolPlugin({
                filename: '[file].map',
                exclude: ['async-plotlyjs']
            }),
            new NodePolyfillPlugin()
        ]
    };
};
