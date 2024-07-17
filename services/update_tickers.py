from services.polygon_service import PolygonService
import os
from dotenv import load_dotenv

from services.thetadata_service import ThetadataService
from supabase import create_client, Client


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

url: str = os.environ.get("SUPABASE_URL", None)
key: str = os.environ.get("SUPABASE_KEY", None)
try:
    supabase: Client = create_client(url, key)
except Exception as e:
    print(e)
    raise e


polygon = PolygonService()
tickers = polygon.update_db_tickers(supabase)
print("Updated tickers completed")
