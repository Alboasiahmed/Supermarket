import os
import sys
import pandas as pd
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# Path to the MYOB export. Change this if the file lives somewhere else,
# or pass a path on the command line:  python "imported items.py" C:\path\Stock.txt
STOCK_FILE = r"C:\Users\alboa\Downloads\Stock.txt"

# Maps our database fields -> the EXACT column names in Stock.txt
COLUMN_MAP = {
    "barcode":       "Barcode",
    "item_name":     "Description",
    "extended_desc": "Extended_Desc",
    "retail_price":  "Sell",
    "cost_price":    "Cost",
    "unit":          "UnitOf_Measure",
    "reorder_point": "Min_Qty",
    "category":      "Department",
    "subcat_1":      "CatHeader_1",
    "subcat_2":      "CatHeader_2",
    "inactive":      "Inactive",
}

# The CatHeader columns sometimes contain MYOB placeholder junk
# ("Category 3", "Oters", etc.) instead of a real subcategory tag.
PLACEHOLDER_TAGS = {"", "category 1", "category 2", "category 3", "oters", "others"}


def clean_price(value):
    return float(str(value).replace("$", "").replace(",", "").strip() or 0)


def clean_int(value):
    try:
        return int(float(str(value).strip() or 0))
    except (ValueError, TypeError):
        return 0


def clean_tag(value):
    """Return a real subcategory tag, or '' if it's blank/placeholder junk."""
    tag = str(value).strip()
    return "" if tag.lower() in PLACEHOLDER_TAGS else tag


def build_description(row):
    """Extended_Desc is empty for these items, so fall back to the CatHeader
    subcategory tags (e.g. 'Rusk Biscuits'). This keeps the field useful and
    gives the search/embedding step more words to match on."""
    extended = str(row.get(COLUMN_MAP["extended_desc"], "")).strip()
    if extended:
        return extended
    tags = [clean_tag(row.get(COLUMN_MAP["subcat_1"], "")),
            clean_tag(row.get(COLUMN_MAP["subcat_2"], ""))]
    tags = [t for t in tags if t]
    return " ".join(tags) or None


def get_or_create_category(name):
    name = name.strip()
    if not name:
        return None
    result = supabase.table("categories").select("category_id").eq("category_name", name).execute()
    if result.data:
        return result.data[0]["category_id"]
    result = supabase.table("categories").insert({"category_name": name}).execute()
    return result.data[0]["category_id"]


def import_items(path):
    # Stock.txt is TAB-separated with quoted values.
    #  - sep="\t"            : split on tabs, not commas (descriptions contain commas)
    #  - dtype=str           : keep long barcodes exact (no float/scientific notation)
    #  - keep_default_na=False : blank cells become "" instead of NaN, so .strip() is safe
    read_kwargs = dict(sep="\t", dtype=str, keep_default_na=False, on_bad_lines="skip")
    try:
        df = pd.read_csv(path, encoding="utf-8", **read_kwargs)
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="latin-1", **read_kwargs)

    print(f"Columns in your file:\n{list(df.columns)}\n")
    print(f"Total rows: {len(df)}")
    print("Starting import...\n")

    inserted = 0
    skipped = 0

    for _, row in df.iterrows():
        try:
            # This export has no 'Stock Code' column, so the Barcode (which also
            # holds custom codes like CS1 / Paneer1) is our unique key.
            barcode = str(row.get(COLUMN_MAP["barcode"], "")).strip()
            if not barcode:
                skipped += 1
                print(f"  skipped row {inserted + skipped}: missing barcode")
                continue

            # Inactive: "0" = active, "1" = inactive. We keep the record but flag it.
            is_active = clean_int(row.get(COLUMN_MAP["inactive"], 0)) == 0

            category_id = get_or_create_category(
                str(row.get(COLUMN_MAP["category"], ""))
            )

            item = {
                "sku":           barcode,
                "barcode":       barcode,
                "item_name":     str(row.get(COLUMN_MAP["item_name"], "")).strip(),
                "description":   build_description(row),
                "retail_price":  clean_price(row.get(COLUMN_MAP["retail_price"], 0)),
                "cost_price":    clean_price(row.get(COLUMN_MAP["cost_price"], 0)),
                "unit":          str(row.get(COLUMN_MAP["unit"], "")).strip() or None,
                "reorder_point": clean_int(row.get(COLUMN_MAP["reorder_point"], 0)),
                "category_id":   category_id,
                "is_active":     is_active,
            }

            supabase.table("items").upsert(item, on_conflict="sku").execute()

            inserted += 1
            if inserted % 100 == 0:
                print(f"  {inserted} / {len(df)} imported...")

        except Exception as e:
            skipped += 1
            print(f"  skipped row {inserted + skipped}: {e}")

    print(f"\nFinished. {inserted} items imported, {skipped} skipped.")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else STOCK_FILE
    import_items(path)
