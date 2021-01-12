/*
Plotly Dash integration boiler plate code.
*/
window.onload = function() {
    // setup url for application end point
    const appPrefix = 'dash'
    const appUrl = getWebAppBackendUrl('/' + appPrefix + '/')
    // setup url for app configuration
    const configUrl = getWebAppBackendUrl('/configure')
    const args = '?webAppBackendUrl=' + encodeURIComponent(getWebAppBackendUrl('/')) + '&appPrefix=' + appPrefix;
    // do the magic
    fetch( configUrl + args )
   .then(async r=> {
       const json = await r.json()
       // if there is no error, redirect to Dash app
       if (!json.error) {
           location.replace(appUrl)
       }
       // otherwise, output the error to the page
       else {
           document.write(json.error);
       }
   }).catch(e=>console.error('Boo...' + e));
}