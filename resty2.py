import streamlit as st
import requests
import pandas as pd
import json
from urllib.parse import urljoin

#------------------------------------------------------
# Salesforce RESTY Streamlit Application
# Author: Mohan Chinnappan
# Copyleft software. Maintain the author name in your copies/modifications
#------------------------------------------------------

# Custom CSS for modern UI
st.markdown("""
    <style>
    .main {
        background-color: #f5f7fa;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .stButton>button {
        background-color: #0078d4;
        color: white;
        border-radius: 5px;
        padding: 10px 20px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #005a9e;
    }
    .stTextInput>label, .stSelectbox>label, .stCheckbox>label {
        font-weight: bold;
        color: #333;
    }
    .stSidebar {
        background-color: #e9ecef;
        padding: 20px;
        border-radius: 10px;
    }
    .stSidebar .stMarkdown {
        font-size: 14px;
    }
    </style>
""", unsafe_allow_html=True)

def load_auth_credentials(auth_file):
    """Loads Salesforce credentials and API version from an auth.json file with nested result structure."""
    auth_data = json.load(auth_file)
    # Access the 'result' object
    result = auth_data.get('result', {})
    access_token = result.get('accessToken')
    instance_url = result.get('instanceUrl')
    api_version = result.get('apiVersion', '60.0')  # Default to 60.0 if missing

    if not access_token or not instance_url:
        raise ValueError("Missing required credentials (accessToken or instanceUrl) in auth.json under 'result'")

    return {
        'access_token': access_token,
        'instance_url': instance_url,
        'api_version': api_version
    }

def determine_record_key(endpoint_path, response_json):
    """Determines the key to use for accessing records based on the endpoint."""
    endpoint_key = endpoint_path.split('/')[-1]
    if endpoint_key in response_json:
        return endpoint_key
    return next(iter(response_json.keys()), 'records')

def fetch_data(method, full_url, headers, instance_url, endpoint_path, all_pages=False, payload=None, soql_query=None):
    """Fetches or modifies data using the specified HTTP method, with support for SOQL queries."""
    method = method.upper()
    all_records = []
    response_json = None

    if method == "GET":
        if 'query' in endpoint_path.lower() and soql_query:
            params = {'q': soql_query}
        else:
            params = None

        while full_url:
            try:
                response = requests.get(full_url, headers=headers, params=params)
                if response.status_code != 200:
                    st.error(f"Failed to fetch data: {response.status_code} {response.text}")
                    st.write("Raw Response:", response.text)
                    return None, None
                
                try:
                    response_json = response.json()
                except json.JSONDecodeError as e:
                    st.error(f"Failed to parse response as JSON: {e}")
                    st.write("Raw Response:", response.text)
                    return None, None

                if 'query' in endpoint_path.lower():
                    all_records.extend(response_json.get('records', []))
                    if all_pages and 'nextRecordsUrl' in response_json:
                        st.write(f"Next Records URL: {response_json['nextRecordsUrl']}")
                        full_url = urljoin(instance_url, response_json['nextRecordsUrl'])
                        params = None
                    else:
                        full_url = None
                else:
                    record_key = determine_record_key(endpoint_path, response_json)
                    all_records.extend(response_json.get(record_key, []))
                    if all_pages and 'nextPageUrl' in response_json and response_json['nextPageUrl'] is not None:
                        st.write(f"Next Page URL: {response_json['nextPageUrl']}")
                        full_url = urljoin(instance_url, response_json['nextPageUrl'])
                    else:
                        full_url = None

            except requests.RequestException as e:
                st.error(f"Request failed: {e}")
                return None, None
        return all_records, response_json

    elif method == "POST":
        response = requests.post(full_url, headers=headers, json=payload)
        if response.status_code not in (200, 201):
            st.error(f"Failed to create data: {response.status_code} {response.text}")
            return None, None
        response_json = response.json()
        return response_json, response_json

    elif method == "PATCH":
        response = requests.patch(full_url, headers=headers, json=payload)
        if response.status_code != 204:
            st.error(f"Failed to update data: {response.status_code} {response.text}")
            return None, None
        response_json = response.json() if response.content else {"message": "Update successful"}
        return response_json, response_json

    elif method == "DELETE":
        response = requests.delete(full_url, headers=headers)
        if response.status_code != 204:
            st.error(f"Failed to delete data: {response.status_code} {response.text}")
            return None, None
        response_json = {"message": "Delete successful"}
        return response_json, response_json

    else:
        st.error(f"Unsupported HTTP method: {method}")
        return None, None

def generate_node_js_code(method, full_url, headers, instance_url, endpoint_path, all_pages=False, payload=None, soql_query=None):
    """Generates equivalent Node.js code for the API operation with command-line auth.json support and nested result structure."""
    base_code = """
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
        const authData = JSON.parse(fs.readFileSync(authFilePath, 'utf8'));
        const auth = authData.result; // Access the 'result' object
        const instanceUrl = auth.instanceUrl;
        const accessToken = auth.accessToken;
        
        if (!accessToken || !instanceUrl) {
            throw new Error('Missing required credentials (accessToken or instanceUrl) in auth.json under "result"');
        }
        
        return { instanceUrl, accessToken };
    } catch (error) {
        console.error('Failed to load auth.json:', error.message);
        process.exit(1);
    }
}
"""
    
    if method == "GET":
        if 'query' in endpoint_path.lower() and soql_query:
            escaped_soql_query = soql_query.replace("'", "\\'")
            node_js_code = f"""{base_code}
async function fetchData() {{
    try {{
        const {{ instanceUrl, accessToken }} = await loadAuthCredentials();
        const headers = {{
            'Authorization': `Bearer ${{accessToken}}`,
            'Content-Type': 'application/json'
        }};
        
        let allRecords = [];
        let url = '{full_url}?q={escaped_soql_query}';
        
        while (url) {{
            const response = await axios.get(url, {{ headers }});
            const data = response.data;
            allRecords = allRecords.concat(data.records || []);
            url = {(f"'{instance_url}' + data.nextRecordsUrl" if all_pages else "null")};
        }}
        console.log(JSON.stringify(allRecords));
    }} catch (error) {{
        console.error('Error:', error.response ? error.response.data : error.message);
    }}
}}

fetchData();
"""
        else:
            node_js_code = f"""{base_code}
async function fetchData() {{
    try {{
        const {{ instanceUrl, accessToken }} = await loadAuthCredentials();
        const headers = {{
            'Authorization': `Bearer ${{accessToken}}`,
            'Content-Type': 'application/json'
        }};
        
        let allRecords = [];
        let url = '{full_url}';
        
        while (url) {{
            const response = await axios.get(url, {{ headers }});
            const data = response.data;
            const recordKey = Object.keys(data).includes('{endpoint_path.split('/')[-1]}') ? 
                '{endpoint_path.split('/')[-1]}' : Object.keys(data)[0] || 'records';
            allRecords = allRecords.concat(data[recordKey] || []);
            url = {(f"'{instance_url}' + data.nextPageUrl" if all_pages else "null")};
        }}
        console.log(JSON.stringify(allRecords));
    }} catch (error) {{
        console.error('Error:', error.response ? error.response.data : error.message);
    }}
}}

fetchData();
"""
    elif method == "POST":
        node_js_code = f"""{base_code}
async function createData() {{
    try {{
        const {{ instanceUrl, accessToken }} = await loadAuthCredentials();
        const headers = {{
            'Authorization': `Bearer ${{accessToken}}`,
            'Content-Type': 'application/json'
        }};
        
        const payload = {json.dumps(payload)};
        const response = await axios.post('{full_url}', payload, {{ headers }});
        console.log('Response:', response.data);
    }} catch (error) {{
        console.error('Error:', error.response ? error.response.data : error.message);
    }}
}}

createData();
"""
    elif method == "PATCH":
        node_js_code = f"""{base_code}
async function updateData() {{
    try {{
        const {{ instanceUrl, accessToken }} = await loadAuthCredentials();
        const headers = {{
            'Authorization': `Bearer ${{accessToken}}`,
            'Content-Type': 'application/json'
        }};
        
        const payload = {json.dumps(payload)};
        const response = await axios.patch('{full_url}', payload, {{ headers }});
        console.log('Response:', response.data || 'Update successful');
    }} catch (error) {{
        console.error('Error:', error.response ? error.response.data : error.message);
    }}
}}

updateData();
"""
    elif method == "DELETE":
        node_js_code = f"""{base_code}
async function deleteData() {{
    try {{
        const {{ instanceUrl, accessToken }} = await loadAuthCredentials();
        const headers = {{
            'Authorization': `Bearer ${{accessToken}}`,
            'Content-Type': 'application/json'
        }};
        
        const response = await axios.delete('{full_url}', {{ headers }});
        console.log('Response:', 'Delete successful');
    }} catch (error) {{
        console.error('Error:', error.response ? error.response.data : error.message);
    }}
}}

deleteData();
"""
    else:
        node_js_code = "// Unsupported HTTP method"
    
    return node_js_code

def main():
    st.title("Salesforce RESTY")

    # Sidebar for configuration and help
    with st.sidebar:
        st.header("Configuration & Help")
        st.markdown("""
        **Get `auth.json`:**
        1. Login to your org:
           ```bash
           sf force auth web login -r https://login.salesforce.com
           ```
           Or for sandboxes:
           ```bash
           sf force auth web login -r https://test.salesforce.com
           ```
        2. Export credentials:
           ```bash
           sf force org display -u <username> --json > auth.json
           ```
        **Expected auth.json format:**
        ```json
        {
          "status": 0,
          "result": {
            "id": "00DHs000000QASYMA4",
            "apiVersion": "63.0",
            "accessToken": "your_access_token",
            "instanceUrl": "https://yourinstance.salesforce.com"
          }
        }
        ```
        **Examples:**
        - GET: `/services/data/v{version}/sobjects/Account`
        - SOQL Query: `/services/data/v{version}/query`  
          Query: `SELECT Name FROM Account`
        - POST: `/services/data/v{version}/sobjects/Account`  
          Payload: `{"Name": "New Account"}`
        - PATCH: `/services/data/v{version}/sobjects/Account/{recordId}`  
          Payload: `{"Name": "Updated Account"}`
        - DELETE: `/services/data/v{version}/sobjects/Account/{recordId}`
        """)

        # Upload auth.json file
        auth_json = st.file_uploader("Upload auth.json", type=['json'])

    # Main content in a container
    if auth_json is not None:
        with st.container():
            auth_credentials = load_auth_credentials(auth_json)
            instance_url = auth_credentials['instance_url'].strip()
            if not instance_url.startswith(('http://', 'https://')):
                instance_url = 'https://' + instance_url
            api_version_default = auth_credentials['api_version']

            # API Version input with dynamic default from auth.json
            api_version = st.text_input(
                "API Version",
                value=api_version_default,
                help="Enter the Salesforce API version (e.g., 60.0). Loaded from auth.json if available, defaults to 60.0."
            )

            # Layout with columns
            col1, col2 = st.columns([1, 2])
            with col1:
                method = st.selectbox("HTTP Method", ["GET", "POST", "PATCH", "DELETE"])
            with col2:
                endpoint_path = st.text_input(
                    "Endpoint Path",
                    value=f"/services/data/v{api_version}/sobjects/Account" if method == "GET" else f"/services/data/v{api_version}/sobjects/",
                    help="Enter the REST API endpoint path (e.g., /services/data/v60.0/query for SOQL)"
                )

            # SOQL query input if endpoint is /query
            soql_query = None
            if method == "GET" and 'query' in endpoint_path.lower():
                soql_query = st.text_area(
                    "SOQL Query",
                    value="SELECT Name FROM Account",
                    height=100,
                    help="Enter your SOQL query (e.g., SELECT Name FROM Account)"
                )
                if not soql_query.strip():
                    st.error("SOQL query is required for /query endpoint")
                    return

            # Additional options
            all_pages = st.checkbox("Fetch all pages", disabled=method != "GET", help="Only applicable for GET requests")

            if method in ["POST", "PATCH"]:
                payload_input = st.text_area(
                    "JSON Payload",
                    value='{"Name": "New Account"}' if method == "POST" else '{}',
                    height=100,
                    help="Enter the JSON payload for POST or PATCH requests"
                )
                try:
                    payload = json.loads(payload_input) if payload_input.strip() else None
                except json.JSONDecodeError:
                    st.error("Invalid JSON payload")
                    return
            else:
                payload = None

            if st.button(f"Execute {method}", key="execute"):
                if not endpoint_path:
                    st.error("Endpoint path is required.")
                    return

                full_url = urljoin(instance_url, endpoint_path)
                headers = {
                    'Authorization': f'Bearer {auth_credentials["access_token"]}',
                    'Content-Type': 'application/json'
                }

                try:
                    data, last_response = fetch_data(method, full_url, headers, instance_url, endpoint_path, all_pages, payload, soql_query)
                    if data is None:
                        return

                    # Display results
                    if method == "GET" and data:
                        df = pd.DataFrame(data)
                        st.dataframe(df, use_container_width=True)
                        csv = df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="Download CSV",
                            data=csv,
                            file_name='salesforce_data.csv',
                            mime='text/csv'
                        )
                    elif method in ["POST", "PATCH", "DELETE"]:
                        st.success(f"{method} request completed successfully")
                        st.json(data)

                    st.subheader("Request Details")
                    st.code(full_url + (f"?q={soql_query}" if soql_query else ""), language="http")
                    if last_response:
                        st.subheader("Response JSON")
                        st.json(last_response)

                    if not data:
                        st.warning("No data returned.")

                    # Display Node.js equivalent code
                    st.subheader("Node.js Equivalent Code")
                    node_js_code = generate_node_js_code(method, full_url, headers, instance_url, endpoint_path, all_pages, payload, soql_query)
                    st.code(node_js_code, language="javascript")
                    st.markdown("""
                    **To run in Node.js:**
                    1. Install dependencies: `npm install axios`
                    2. Save the code as `salesforce_rest.js`
                    3. Run with auth file: `node salesforce_rest.js path/to/auth.json`
                       - Or run without arg and enter path: `node salesforce_rest.js`
                    """)

                except Exception as e:
                    st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()