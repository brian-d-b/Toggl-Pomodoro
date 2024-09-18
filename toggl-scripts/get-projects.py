import requests
import base64
import json

# Load the API key from config.json
with open('./config.json') as config_file:
    config = json.load(config_file)
    api_key = config['api_key']


# API Token (replace with your actual API token)

encoded_credentials = base64.b64encode(f"{api_key}:api_token".encode()).decode()

# Headers for the request
headers = {
    'Authorization': f'Basic {encoded_credentials}',
    'Content-Type': 'application/json'
}

# Workspace ID (replace with your actual workspace ID)
workspace_id = 8404611  # Replace with your actual workspace ID

# API URL to fetch projects
url = f'https://api.track.toggl.com/api/v9/workspaces/{workspace_id}/projects'

# Send GET request to the Toggl API
response = requests.get(url, headers=headers)

# Check if the request was successful
if response.status_code == 200:
    # Parse the response JSON if successful
    projects = response.json()
    print("Projects:", projects)
else:
    # Print the error if the request failed
    print(f"Failed to fetch projects. Status code: {response.status_code}")
    print("Response:", response.text)
