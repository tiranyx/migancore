"""Onamix organ — MCP browser automation suite.

NOTE: This is a thin wrapper during migration. Full implementation lives
in tool_executor.py until full refactor is complete and tested.
"""

from typing import Any

# Re-export handlers from legacy module for now
from tool_executor import (
    _onamix_get as onamix_get,
    _onamix_search as onamix_search,
    _onamix_scrape as onamix_scrape,
    _onamix_post as onamix_post,
    _onamix_crawl as onamix_crawl,
    _onamix_history as onamix_history,
    _onamix_links as onamix_links,
    _onamix_config as onamix_config,
    _onamix_multi as onamix_multi,
)

HANDLERS: dict[str, Any] = {
    "onamix_get": onamix_get,
    "onamix_search": onamix_search,
    "onamix_scrape": onamix_scrape,
    "onamix_post": onamix_post,
    "onamix_crawl": onamix_crawl,
    "onamix_history": onamix_history,
    "onamix_links": onamix_links,
    "onamix_config": onamix_config,
    "onamix_multi": onamix_multi,
}
