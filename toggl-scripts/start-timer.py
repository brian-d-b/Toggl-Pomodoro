import requests
import base64
import argparse
from datetime import datetime, timezone
import json

# Load the API key from config.json
with open('./config.json') as config_file:
    config = json.load(config_file)
    api_key = config['api_key']

# Parse the description argument from the command line
parser = argparse.ArgumentParser(description="Start a new Toggl time entry.")
parser.add_argument('--description', type=str, required=True, help='Description for the time entry')
args = parser.parse_args()

description = args.description

encoded_credentials = base64.b64encode(f"{api_key}:api_token".encode()).decode()
headers = {
    'Authorization': f'Basic {encoded_credentials}',
    'Content-Type': 'application/json'
}

# Get workspace ID (You'll need to replace this with your actual workspace ID)
workspace_id = 8404611  # Replace with your workspace ID

# Get the current time in UTC
current_time_utc = datetime.now(timezone.utc).isoformat()

new_time_entry = {
    "description": description,
    "duration": -1,  # Indicates a running time entry
    "created_with": "python_script",  # Or any other string you want
    "start": current_time_utc,  # Current time in UTC
    "workspace_id": workspace_id,  # Include workspace ID
    "project_id": 204411781  # Replace with your actual project ID
}

# Make the API request
response = requests.post(f'https://api.track.toggl.com/api/v9/workspaces/{workspace_id}/time_entries',
                         headers=headers, json=new_time_entry)

# Handle the response
if response.status_code == 200:
    created_entry = response.json()
    print("Time entry created successfully!")
    print(created_entry)
else:
    print(f"Error creating time entry: {response.status_code}, {response.text}")
