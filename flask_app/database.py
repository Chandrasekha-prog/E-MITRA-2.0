import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# Initialize Supabase client
def get_supabase_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Critical Error: SUPABASE_URL or SUPABASE_KEY is missing from environment variables. Please check your .env file.")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase_client()
