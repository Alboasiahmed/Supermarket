import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv(override=True)   # make .env win over any stale OS environment variable

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")



USE_AI = os.getenv("USE_AI", "false").lower() == "true"
openai_client = None
if USE_AI and os.getenv("OPENAI_API_KEY"):
    from openai import OpenAI
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    
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




def ai_reply(query, products):
    product_list = format_search_reply(products)   
    resp = openai_client.chat.completions.create(
        model="gpt-5.4-nano",   
        messages=[
            {"role": "system", "content":
             "You are a friendly assistant for Swagat India Groceries. "
             "Recommend ONLY items from the product list. Keep it short and warm. "
             "Reply in plain text only - do NOT use Markdown, asterisks, bold, or headings."},
            {"role": "user", "content":
             f"Question: {query}\n\nProducts:\n{product_list}"},
        ],
        max_completion_tokens=300,   # gpt-5.x models use this instead of max_tokens
    )
    return resp.choices[0].message.content


@app.post("/chat")
def chat(req: ChatRequest):
    products = search_products(req.message)

    if openai_client and products:
        try:
            return {"reply": ai_reply(req.message, products),
                    "products": products, "mode": "ai"}
        except Exception:
            pass

    return {"reply": format_search_reply(products), "products": products, "mode": "search"}