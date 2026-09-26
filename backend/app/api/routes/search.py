from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.product import ProductSearchResult, SearchRequest
from app.services.product_service import search_products

router = APIRouter()


@router.post("/search", response_model=List[ProductSearchResult])
async def search(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Search for products by natural-language query or marketplace URL.

    Examples:
    - "iPhone 16 128GB"
    - "https://www.amazon.in/dp/B0CHX1W1XY"
    - "Sony WH-1000XM5 headphones"
    """
    return await search_products(db, request.query, request.marketplace)
