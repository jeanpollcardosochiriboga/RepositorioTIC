// §4 metrics — backend latency middleware
const metricsMW = require('./metrics_middleware');

module.exports = {
    flowFile: "flows.json",
    flowFilePretty: true,
    uiPort: process.env.PORT || 1880,
    httpAdminRoot: "/admin",
    httpNodeRoot: "/",
    httpStatic: "/data/www",
    httpNodeMiddleware: metricsMW,
    editorTheme: {
        projects: { enabled: false }
    }
};
