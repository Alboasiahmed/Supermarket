import os
import pandas as pd
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

COLUMN_MAP = {
    "sku":           "Stock Code",
    "barcode":       "Barcode",
    "item_name":     "Description",
    "description":   "Notes",
    "retail_price":  "Sell Price Inc",
    "cost_price":    "Cost Price",
    "unit":          "Unit",
    "reorder_point": "Reorder Level",
    "on_hand":       "On Hand",
    "category":      "Department",
}


def clean_price(value):
    return float(str(value).replace("$", "").replace(",", "").strip() or 0)


def clean_int(value):
    try:
        return int(float(str(value).strip() or 0))
    except:
        return 0


def get_or_create_category(name):
    name = name.strip()
    if not name:
        return None
    result = supabase.table("categories").select("category_id").eq("category_name", name).execute()
    if result.data:
        return result.data[0]["category_id"]
    result = supabase.table("categories").insert({"category_name": name}).execute()
    return result.data[0]["category_id"]


def import_items(csv_path):
    try:
        df = pd.read_csv(csv_path, encoding="utf-8", on_bad_lines="skip")
    except UnicodeDecodeError:
        df = pd.read_csv(csv_path, encoding="latin-1", on_bad_lines="skip")

    print(f"Columns in your CSV:\n{list(df.columns)}\n")
    print(f"Total rows: {len(df)}")
    print("Starting import...\n")

    inserted = 0
    skipped = 0

    for _, row in df.iterrows():
        try:
            category_id = get_or_create_category(str(row.get(COLUMN_MAP["category"], "")))

            item = {
                "sku":           str(row[COLUMN_MAP["sku"]]).strip(),
                "barcode":       str(row.get(COLUMN_MAP["barcode"], "")).strip() or None,
                "item_name":     str(row[COLUMN_MAP["item_name"]]).strip(),
                "description":   str(row.get(COLUMN_MAP["description"], "")).strip() or None,
                "retail_price":  clean_price(row[COLUMN_MAP["retail_price"]]),
                "cost_price":    clean_price(row.get(COLUMN_MAP["cost_price"], 0)),
                "unit":          str(row.get(COLUMN_MAP["unit"], "")).strip() or None,
                "reorder_point": clean_int(row.get(COLUMN_MAP["reorder_point"], 0)),
                "category_id":   category_id,
                "is_active":     True,
            }

            result = supabase.table("items").upsert(item, on_conflict="sku").execute()
            item_id = result.data[0]["item_id"]

            
            on_hand = clean_int(row.get(COLUMN_MAP["on_hand"], 0))
            if on_hand != 0:
                supabase.table("stock_movements").insert({
                    "item_id":       item_id,
                    "change_qty":    on_hand,
                    "movement_type": "initial_count",
                }).execute()

            inserted += 1
            if inserted % 100 == 0:
                print(f"  {inserted} / {len(df)} imported...")

        except Exception as e:
            skipped += 1
            print(f"  skipped row {inserted + skipped}: {e}")

    print(f"\nFinished. {inserted} items imported, {skipped} skipped.")


if __name__ == "__main__":
    import_items("stock_export.csv")