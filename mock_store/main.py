"""Isolated development rehearsal. Run with uvicorn mock_store.main:app."""
import json
from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

ROOT = Path(__file__).parent
app = FastAPI(title="Mock T-shirt catalog", version="0.1.0")


def catalog():
    data = json.loads((ROOT / "catalog.json").read_text())
    for product in data["products"]:
        product["variants"] = [
            {"sku": f"DEMO-{product['id']}-{colour.upper()}-{size}",
             "colour": colour, "size": size, "stock": 0}
            for colour, _ in product["colours"] for size in data["sizes"]
        ]
    return data


def render_preview():
    payload = json.dumps(catalog(), ensure_ascii=False).replace("<", r"\u003c")
    return (ROOT / "preview.html").read_text().replace("__CATALOG_DATA__", payload)


@app.get("/", response_class=HTMLResponse)
def preview():
    from .build import render
    return render(server=True)


@app.get("/mock/catalog")
def get_catalog(audience: Literal["Men", "Women"] | None = None):
    data = catalog()
    if audience:
        data["products"] = [p for p in data["products"] if p["audience"] == audience]
    return data


from .sandbox import router as sandbox_router
app.include_router(sandbox_router)
