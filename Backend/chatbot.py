import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

app = FastAPI()

# Let the website (different port) talk to this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # we'll lock this down before going live
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


def search_products(query, k=5):
    vector = model.encode(query).tolist()
    res = supabase.rpc("match_items",
                       {"query_embedding": vector, "match_count": k}).execute()
    return res.data or []


def format_search_reply(products):
    if not products:
        return "Sorry, I couldn't find anything matching that in our store."
    lines = [f"- {p['item_name']} (${float(p['retail_price']):.2f})" for p in products]
    return "Here's what we have that matches:\n" + "\n".join(lines)


@app.post("/chat")
def chat(req: ChatRequest):
    products = search_products(req.message)
    return {"reply": format_search_reply(products), "products": products, "mode": "search"}