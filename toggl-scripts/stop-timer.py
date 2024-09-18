import requests
import base64

api_token = "5a1d042727316a2c670056754c38c29e"
encoded_credentials = base64.b64encode(f"{api_token}:api_token".encode()).decode()
headers = {
    'Authorization': f'Basic {encoded_credentials}',
    'Content-Type': 'application/json'
}

# Replace with your actual workspace ID
workspace_id = 8404611

# 1. Get the currently running time entry
response = requests.get('https://api.track.toggl.com/api/v9/me/time_entries/current', headers=headers)

if response.status_code == 200:
    try:
        current_entry = response.json()

        # Since the response is the time entry object directly
        if current_entry and 'id' in current_entry:
            time_entry_id = current_entry['id']

            # 2. Stop the time entry
            stop_response = requests.patch(
                f'https://api.track.toggl.com/api/v9/workspaces/{workspace_id}/time_entries/{time_entry_id}/stop',
                headers=headers
            )

            if stop_response.status_code == 200:
                print("Time entry stopped successfully!")
            else:
                print(f"Error stopping time entry: {stop_response.status_code}, {stop_response.text}")
        else:
            print("No running time entry found.")
    except (ValueError, KeyError) as e:
        print(f"Unexpected API response: {e}")
elif response.status_code == 404:
    print("No running time entry found.")
else:
    print(f"Error getting current time entry: {response.status_code}, {response.text}")
