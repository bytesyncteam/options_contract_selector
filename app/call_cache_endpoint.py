import requests
from dotenv import load_dotenv
import os

load_dotenv()
base_url = os.environ.get("BASE_URL")

requests.post(base_url + f"/update_cache/")