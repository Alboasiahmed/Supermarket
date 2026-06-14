import os
from supabase import create_client
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# all-MiniLM-L6-v2 produces 384-dimension vectors, so your
# item_embeddings.embedding column must be vector(384) or the upsert fails.
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def category_name(item):
    """Pull the joined category name (handles a dict, a list, or missing)."""
    cat = item.get("categories")
    if isinstance(cat, list):
        cat = cat[0] if cat else None
    if isinstance(cat, dict):
        return cat.get("category_name") or ""
    return ""


def build_text(item):
    # Embed the name + its category (e.g. "Sweets") + the description, which now
    # carries the CatHeader subcategory tags. This gives the search far more to
    # match against than the name alone.
    parts = [
        item.get("item_name") or "",
        category_name(item),
        item.get("description") or "",
    ]
    return " ".join(p for p in parts if p).strip()


def fetch_all_active_items(page_size=1000):
    # Supabase returns at most 1000 rows per request, so we page through with
    # .range() until we've collected every active item.
    all_items = []
    start = 0
    while True:
        batch = (
            supabase.table("items")
            .select("item_id, item_name, description, categories(category_name)")
            .eq("is_active", True)
            .range(start, start + page_size - 1)
            .execute()
            .data
        )
        all_items.extend(batch)
        if len(batch) < page_size:
            break
        start += page_size
    return all_items


def embed_all():
    # Join the category name, and only embed ACTIVE items so discontinued
    # products never show up in the chatbot's search results.
    items = fetch_all_active_items()
    print(f"Found {len(items)} active items to embed.")

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
