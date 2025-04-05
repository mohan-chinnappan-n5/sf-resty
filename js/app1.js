const axios = require('axios');
const fs = require('fs');

// Load credentials from auth.json
const auth = JSON.parse(fs.readFileSync('/Users/saromo/Documents/auth.json', 'utf8'));
const instanceUrl = auth.instance_url || auth.instanceUrl;
const accessToken = auth.access_token || auth.accessToken;

const headers = {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
};

async function fetchData() {
    try {
        let allRecords = [];
        let url = 'https://dhs000000qasyma4-dev-ed.develop.my.salesforce.com/services/data/v60.0/sobjects/Account';

        while (url) {
            const response = await axios.get(url, { headers });
            const data = response.data;
            const recordKey = Object.keys(data).includes('Account') ? 
                'Account' : Object.keys(data)[0] || 'records';
            allRecords = allRecords.concat(data[recordKey] || []);
            url = null;
        }
        console.log('Records:', allRecords);
    } catch (error) {
        console.error('Error:', error.response ? error.response.data : error.message);
    }
}

fetchData();
