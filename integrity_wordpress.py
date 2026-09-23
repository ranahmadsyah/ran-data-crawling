import os
import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()

WP_URL = os.getenv("WP_URL")
WP_USERNAME = os.getenv("WP_USERNAME")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")

url = f"{WP_URL}/wp-json/wp/v2/posts"

response = requests.get(
    url,
    auth=HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD),
    timeout=30
)

print("Status:", response.status_code)
print("Response:")
print(response.text[:2000])