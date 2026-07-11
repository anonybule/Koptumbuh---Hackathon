from typing import TypeVar, Generic, Optional, Any
from math import ceil
from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    meta: Optional[dict] = None


class ApiErrorBody(BaseModel):
    success: bool = False
    error: dict


class PaginationMeta(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int


def paginate(page: int = 1, per_page: int = 20, total: int = 0) -> dict:
    page = max(1, page)
    per_page = min(max(1, per_page), 100)
    return {
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": max(1, ceil(total / per_page)) if total else 0,
    }


def offset_limit(page: int = 1, per_page: int = 20) -> tuple[int, int]:
    page = max(1, page)
    per_page = min(max(1, per_page), 100)
    return (page - 1) * per_page, per_page


def ok(data: Any = None, meta: dict | None = None) -> dict:
    return {"success": True, "data": data, "meta": meta}


def err(code: str, message: str, details: dict | None = None) -> dict:
    body: dict = {"code": code, "message": message}
    if details:
        body["details"] = details
    return {"success": False, "error": body}
