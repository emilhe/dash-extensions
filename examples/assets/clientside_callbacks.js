window.dash_clientside = Object.assign({}, window.dash_clientside, {
    clientside: {
        hello: function(n_clicks) {
            console.info('Hello from clientside_callbacks.js! Click count = ' + n_clicks);
        }
    }
});
