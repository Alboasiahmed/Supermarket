# Swagat Supermarket — AI Website & Chatbot

A responsive website and an AI **"Store Expert" chatbot** for a real Indian grocery store. A customer asks a plain-English question (e.g. *"what do I need for biryani?"*) and the bot finds matching products by **meaning** (semantic search over the store's ~6,186-product catalogue) and replies in natural language, grounded only in products the store actually stocks.

🔗 **Live:** https://dtfi2l3y6igh2.cloudfront.net
🧑‍💻 Built solo for a real client · 📄 Full write-up in [`PROJECT_DEBRIEF.md`](PROJECT_DEBRIEF.md) · 🛠️ Build log in [`CHATBOT_PROGRESS.md`](CHATBOT_PROGRESS.md)

---

## Features

- **Responsive storefront** — single-page site, no build step (plain HTML/CSS/JS).
- **Semantic product search** — 384-dim embeddings (`all-MiniLM-L6-v2`) + pgvector cosine similarity.
- **RAG chatbot** — retrieved products are passed to an LLM (`gpt-5.4-nano`) that recommends *only* from that list.
- **Graceful fallback** — if the LLM is disabled (`USE_AI=false`) or fails, the bot auto-degrades to free search-only results. The owner controls AI spend with one flag.
- **Production-hardened API** — per-IP rate limiting, input-length cap, locked-down CORS.

---

## Architecture

**Offline pipeline (run once):** `Stock.txt` (MYOB POS export) → `imported items.py` → Supabase `items` → `embed_items.py` → `item_embeddings` (vector 384).

**Online path:** Browser → **CloudFront** (HTTPS) → `/chat` routes to the **Lightsail** FastAPI backend (everything else → **S3**) → backend embeds the query, searches **Supabase** (pgvector `match_items`), and asks **OpenAI** to phrase the reply.

> One CloudFront distribution with two origins (S3 + Lightsail) gives the API free HTTPS and keeps it same-origin with the site. See [`PROJECT_DEBRIEF.md`](PROJECT_DEBRIEF.md) for the full diagram and rationale.

---

## Tech stack

| Layer | Tech |
|---|---|
| Frontend | HTML, CSS, JavaScript (no framework) |
| Backend | Python, FastAPI, Uvicorn |
| Search / ML | `sentence-transformers` (`all-MiniLM-L6-v2`), pgvector |
| LLM | OpenAI `gpt-5.4-nano` |
| Database | Supabase (PostgreSQL + pgvector) |
| Infrastructure | AWS S3, CloudFront, Lightsail (Ubuntu, systemd), IAM, Budgets |
| Security | `slowapi` rate limiting, Pydantic validation, CORS |

---

## Repository structure

```
.
├── index.html              # storefront page
├── CSS/style.css           # site + chat widget styles
├── JS/chatbot.js           # chat client (POSTs to /chat)
├── Images/                 # product & category imagery
├── database/schema.sql     # 7-table schema + vector index + match_items()
├── Backend/
│   ├── chatbot.py          # FastAPI app: /chat (search + RAG + fallback)
│   ├── embed_items.py      # one-time: generate embeddings
│   ├── imported items.py   # one-time: import MYOB POS export
│   ├── test_connection.py  # Supabase connectivity check
│   └── requirements.txt
├── PROJECT_DEBRIEF.md      # detailed project write-up
└── CHATBOT_PROGRESS.md     # build/deployment log
```

---

## Local setup (backend)

```bash
cd Backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
# create .env (see below), then:
uvicorn chatbot:app --reload --port 8000
```

### Environment variables (`Backend/.env` — never commit this)

| Variable | Purpose |
|---|---|
| `SUPABASE_URL` | Supabase project API URL |
| `SUPABASE_KEY` | Supabase **secret** key (backend only) |
| `USE_AI` | `true` to enable the LLM; `false` for free search-only |
| `OPENAI_API_KEY` | OpenAI key (only needed when `USE_AI=true`) |
| `ALLOWED_ORIGINS` | comma-separated allowed origins for CORS (e.g. your site URL) |

---

## Database setup

1. In Supabase, run [`database/schema.sql`](database/schema.sql) (creates the tables, the vector index, and the `match_items` similarity-search function).
2. Load the catalogue: `python "imported items.py"`.
3. Generate embeddings: `python embed_items.py`.

---

## Deployment (AWS, configured via console)

- **S3** — hosts the static site (public-read bucket policy).
- **CloudFront** — HTTPS + CDN; default behaviour → S3, `/chat` behaviour → Lightsail backend.
- **Lightsail** — Ubuntu 22.04 (2 GB) running the FastAPI app under `systemd`, static IP, port 8000 open.

> No infrastructure-as-code yet — deployment is manual. A future improvement would be Terraform/CloudFormation + a CI/CD pipeline.

---

## Roadmap

- [x] Responsive storefront
- [x] Semantic-search + RAG chatbot
- [x] AWS deployment + security hardening
- [ ] **Stock/demand forecasting** (future phase — schema already supports it via `stock_movements` and `reorder_point`)
- [ ] Automated tests, Dockerfile, CI/CD

---

## Notes

- Built solo for a real grocery business; demoed and handed over to the owner.
- No secrets are committed — `.env` is git-ignored and was verified clean in git history.
