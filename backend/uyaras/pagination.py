"""Bounded collection responses with stable pagination metadata."""
from math import ceil
from sqlalchemy import select, func
from .security import require


def page_query(db, query, page=1, page_size=24, render=lambda row: row):
    require(1 <= page <= 10000 and 1 <= page_size <= 100, "Invalid pagination.", 422)
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    rows = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": [render(row) for row in rows], "total": total, "page": page,
            "page_size": page_size, "pages": ceil(total / page_size)}


def page_items(items, page=1, page_size=100):
    require(1 <= page <= 10000 and 1 <= page_size <= 100, "Invalid pagination.", 422)
    return {"items": items[(page-1)*page_size:page*page_size], "total": len(items),
            "page": page, "page_size": page_size, "pages": ceil(len(items)/page_size)}
