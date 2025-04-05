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
    """Loads Salesforce credentials from an auth.json file."""
    auth_data = json.load(auth_file)
    access_token = auth_data.get('access_token') or auth_data.get('accessToken')
    instance_url = auth_data.get('instance_url') or auth_data.get('instanceUrl')

    if not access_token or not instance_url:
        raise ValueError("Missing required credentials in auth.json")

    return {'access_token': access_token, 'instance_url': instance_url}

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
        # Handle SOQL query if the endpoint is /query
        if 'query' in endpoint_path.lower() and soql_query:
            params = {'q': soql_query}
        else:
            params = None

        while full_url:
            try:
                response = requests.get(full_url, headers=headers, params=params)
                #st.write(f"Response Status Code: {response.status_code}")
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

                # Handle SOQL query response
                if 'query' in endpoint_path.lower():
                    all_records.extend(response_json.get('records', []))
                    if all_pages and 'nextRecordsUrl' in response_json:
                        st.write(f"Next Records URL: {response_json['nextRecordsUrl']}")
                        full_url = urljoin(instance_url, response_json['nextRecordsUrl'])
                        params = None  # nextRecordsUrl includes the query, so no params needed
                    else:
                        full_url = None
                else:
                    record_key = determine_record_key(endpoint_path, response_json)
                    all_records.extend(response_json.get(record_key, []))
                    if all_pages and 'nextPageUrl' in response_json and response_json['nextPageUrl'] != None:
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
           sf mohanc hello myorg -u username > auth.json
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

            # API Version input
            api_version = st.text_input("API Version", value="60.0", help="Enter the Salesforce API version (e.g., 60.0)")

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

                except Exception as e:
                    st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()