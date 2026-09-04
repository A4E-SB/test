"""Data models — thin SQL functions over the Database object."""

from . import (blacklist, customers, inquiries, orders, screenshots,
               templates_store)

# Backwards-friendly aliases used across the UI
settings_store = templates_store
templates = templates_store

__all__ = ["blacklist", "customers", "inquiries", "orders", "screenshots",
           "templates_store", "settings_store", "templates"]
