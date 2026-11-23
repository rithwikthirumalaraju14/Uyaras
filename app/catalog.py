from typing import Protocol

from pydantic import BaseModel


class Category(BaseModel):
    id: str
    parent_id: str | None
    slug: str
    name: str


class CategoryPage(BaseModel):
    items: list[Category]
    page: int
    page_size: int


class CatalogStore(Protocol):
    def ready(self) -> bool: ...
    def categories(self, page: int, page_size: int) -> list[dict]: ...


# Starting at published roots keeps children of unpublished branches private.
PUBLIC_CATEGORIES = """
WITH RECURSIVE visible(id, parent_id, slug, name) AS (
    SELECT id, parent_id, slug, name FROM category
    WHERE parent_id IS NULL AND is_published
    UNION ALL
    SELECT c.id, c.parent_id, c.slug, c.name FROM category c
    JOIN visible v ON c.parent_id = v.id WHERE c.is_published
)
SELECT id, parent_id, slug, name FROM visible
ORDER BY slug, id LIMIT :limit OFFSET :offset
"""
