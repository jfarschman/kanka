import requests

# Set your Kanka API Token here
KANKA_API_TOKEN = "PESONAL_API_TOKEN" # Get this from your Kanka.io settings

# API endpoint to list all campaigns
url = "https://api.kanka.io/1.0/campaigns"

headers = {
    "Authorization": f"Bearer {KANKA_API_TOKEN}",
    "Content-Type": "application/json"
}

try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # This will raise an exception for a bad status code
    data = response.json()

    print("Found the following campaigns:")
    for campaign in data.get("data", []):
        print(f"Name: {campaign['name']}, ID: {campaign['id']}")

except requests.exceptions.HTTPError as e:
    print(f"Error: Could not retrieve campaign list. Please check your API token. {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
