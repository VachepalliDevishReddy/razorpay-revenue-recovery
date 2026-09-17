"""SerpApi gateway for RecoverAI Nexus.

Provides a small, testable wrapper around SerpApi's HTTP API. The gateway
returns normalized results and never exposes the API key in returned data.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv(override=True)

SERPAPI_ENDPOINT = "https://serpapi.com/search.json"


class SerpApiError(RuntimeError):
    """Raised when SerpApi cannot complete a request."""


def _clean_result(item: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only useful, display-safe fields from a SerpApi result."""
    return {
        "title": item.get("title", ""),
        "link": item.get("link", ""),
        "snippet": item.get("snippet", ""),
        "source": item.get("source", ""),
        "price": item.get("price", ""),
        "rating": item.get("rating"),
        "reviews": item.get("reviews"),
    }


def search_web(
    query: str,
    *,
    engine: str = "google",
    country: str = "in",
    language: str = "en",
    num: int = 10,
    timeout: int = 20,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Run a SerpApi search and return normalized evidence.

    Required environment variable: SERPAPI_API_KEY.
    """
    query = (query or "").strip()
    key = (api_key or os.getenv("SERPAPI_API_KEY", "")).strip()

    if not query:
        raise ValueError("Search query cannot be empty")
    if not key:
        raise SerpApiError("SERPAPI_API_KEY is not configured")

    params = {
        "api_key": key,
        "engine": engine,
        "q": query,
        "gl": country,
        "hl": language,
        "num": max(1, min(int(num), 100)),
    }

    try:
        response = requests.get(SERPAPI_ENDPOINT, params=params, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise SerpApiError(f"SerpApi request failed: {exc}") from exc
    except ValueError as exc:
        raise SerpApiError("SerpApi returned invalid JSON") from exc

    if payload.get("error"):
        raise SerpApiError(str(payload["error"]))

    organic = payload.get("organic_results", []) or []
    shopping = payload.get("shopping_results", []) or []
    return {
        "query": query,
        "engine": engine,
        "search_information": payload.get("search_information", {}),
        "organic_results": [_clean_result(item) for item in organic],
        "shopping_results": [_clean_result(item) for item in shopping],
        "total_results": len(organic) + len(shopping),
    }


def research_product(product_name: str, *, num: int = 8) -> Dict[str, Any]:
    """Collect Indian web and shopping evidence for a product."""
    product_name = (product_name or "").strip()
    if not product_name:
        raise ValueError("Product name cannot be empty")

    web = search_web(product_name, num=num)
    shopping = search_web(f"{product_name} price", engine="google_shopping", num=num)
    return {
        "product": product_name,
        "web": web,
        "shopping": shopping,
    }


if __name__ == "__main__":
    result = search_web("Razorpay payment recovery")
    print({"query": result["query"], "total_results": result["total_results"]})
