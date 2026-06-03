"""Domain-pack registry."""

from . import banking, ecommerce, healthcare, logistics, saas, telecom

DOMAIN_MODULES = {
    "banking": banking,
    "ecommerce": ecommerce,
    "healthcare": healthcare,
    "logistics": logistics,
    "saas": saas,
    "telecom": telecom,
}
