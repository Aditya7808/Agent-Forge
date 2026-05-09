"""Tool subpackage — submodules are loaded lazily so individual helpers
(e.g. catalogue) can be imported without the full LangChain stack."""

from importlib import import_module
from typing import TYPE_CHECKING

__all__ = [
    "product_search_tool",
    "policy_search_tool",
    "outfit_recommendation_tool",
    "extract_product_codes",
    "fetch_by_codes",
    "search_products",
]

_LAZY = {
    "product_search_tool": ("shoppinggpt.tool.product_search", "product_search_tool"),
    "policy_search_tool": ("shoppinggpt.tool.policy_search", "policy_search_tool"),
    "outfit_recommendation_tool": (
        "shoppinggpt.tool.recommend",
        "outfit_recommendation_tool",
    ),
    "extract_product_codes": (
        "shoppinggpt.tool.catalogue",
        "extract_product_codes",
    ),
    "fetch_by_codes": ("shoppinggpt.tool.catalogue", "fetch_by_codes"),
    "search_products": ("shoppinggpt.tool.catalogue", "search_products"),
}


def __getattr__(name: str):
    if name in _LAZY:
        module_name, attr = _LAZY[name]
        return getattr(import_module(module_name), attr)
    raise AttributeError(f"module 'shoppinggpt.tool' has no attribute {name!r}")


if TYPE_CHECKING:  # pragma: no cover
    from .catalogue import (
        extract_product_codes,
        fetch_by_codes,
        search_products,
    )
    from .policy_search import policy_search_tool
    from .product_search import product_search_tool
    from .recommend import outfit_recommendation_tool
