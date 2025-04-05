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

async function createData() {
    try {
        const { instanceUrl, accessToken } = await loadAuthCredentials();
        const headers = {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json'
        };

        const payload = {"Name": "New Account From RESTY via JS"};
        const response = await axios.post('https://dhs000000qasyma4-dev-ed.develop.my.salesforce.com/services/data/v60.0/sobjects/Account', payload, { headers });
        console.log('Response:', response.data);
    } catch (error) {
        console.error('Error:', error.response ? error.response.data : error.message);
    }
}

createData();
