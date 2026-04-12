const http = require('http');
const options = {
    hostname: 'localhost',
    port: 8000,
    path: '/api/v1/analyses/263aad26-40aa-4dda-bfb6-b0429dc07ab9',
    method: 'GET'
};
const req = http.request(options, (res) => {
    let data = '';
    res.on('data', (d) => data += d);
    res.on('end', () => console.log(data));
});
req.on('error', (e) => console.error(e));
req.end();
