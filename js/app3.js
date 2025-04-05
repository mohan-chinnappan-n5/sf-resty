const axios = require('axios');
const fs = require('fs');
const readline = require('readline');

// Function to load auth credentials
async function loadAuthCredentials() {
    let authFilePath = process.argv[2]; // Get path from command-line argument

    if (!authFilePath) {
        const rl = readline.createInterface({
            input: process.stdin,
            output: process.stdout
        });

        authFilePath = await new Promise(resolve => {
            rl.question('Enter the path to auth.json: ', (answer) => {
                rl.close();
                resolve(answer);
            });
        });
    }

    try {
        const auth = JSON.parse(fs.readFileSync(authFilePath, 'utf8'));
        const instanceUrl = auth.instance_url || auth.instanceUrl;
        const accessToken = auth.access_token || auth.accessToken;

        if (!accessToken || !instanceUrl) {
            throw new Error('Missing required credentials in auth.json');
        }

        return { instanceUrl, accessToken };
    } catch (error) {
        console.error('Failed to load auth.json:', error.message);
        process.exit(1);
    }
}

async function fetchData() {
    try {
        const { instanceUrl, accessToken } = await loadAuthCredentials();
        const headers = {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json'
        };

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