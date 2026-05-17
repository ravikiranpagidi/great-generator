"""Domain-pack registry."""

from . import banking, ecommerce

DOMAIN_MODULES = {
    "banking": banking,
    "ecommerce": ecommerce,
}
