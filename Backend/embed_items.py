import os
from supabase import create_client
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def build_text(item):
    parts = [
        item.get("item_name") or "",
        item.get("brand") or "",
        item.get("description") or "",
    ]
    return " ".join(p for p in parts if p).strip()


def embed_all():
    items = supabase.table("items").select("item_id, item_name, brand, description").execute().data
    print(f"Found {len(items)} items to embed.")

    done = 0
    for item in items:
        text = build_text(item)
        if not text:
            continue

        vector = model.encode(text).tolist()

        supabase.table("item_embeddings").upsert({
            "item_id":   item["item_id"],
            "embedding": vector,
        }).execute()

        done += 1
        if done % 100 == 0:
            print(f"  {done} / {len(items)} embedded...")

    print(f"\nFinished. {done} embeddings created.")


if __name__ == "__main__":
    embed_all()