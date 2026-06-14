"""Quick connection check. Prints the URL (safe) and a MASKED key, then runs
one tiny query so we can see the real error. Safe to delete afterwards."""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

print("SUPABASE_URL =", repr(url))
print("SUPABASE_KEY set?", bool(key),
      "| length:", len(key) if key else 0,
      "| starts:", (key[:6] + "...") if key else None)

print("\nTrying a simple query on 'categories'...")
try:
    sb = create_client(url, key)
    res = sb.table("categories").select("*").limit(1).execute()
    print("OK - query worked. Rows returned:", res.data)
except Exception as e:
    print("ERROR:", repr(e)[:400])
