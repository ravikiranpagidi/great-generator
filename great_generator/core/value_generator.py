"""Faker-backed realistic value generation primitives."""

from __future__ import annotations

import hashlib
import importlib
import random
import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

try:
    _faker_module: Any = importlib.import_module("faker")
except ImportError:  # pragma: no cover - exercised by tests through monkeypatching
    _faker_module = None

FAKER_FACTORY: Any = getattr(_faker_module, "Faker", None)

FIRST_NAMES = [
    "Ava",
    "Liam",
    "Sophia",
    "Noah",
    "Emma",
    "Mia",
    "Ethan",
    "Olivia",
    "Arjun",
    "Priya",
]
LAST_NAMES = [
    "Johnson",
    "Patel",
    "Williams",
    "Brown",
    "Garcia",
    "Smith",
    "Lee",
    "Miller",
    "Davis",
    "Wilson",
]
STREET_NAMES = ["Maple Street", "Oak Avenue", "River Road", "Cedar Lane", "Lake Drive"]
CITIES = ["Springfield", "Austin", "Seattle", "Charlotte", "Denver", "Phoenix"]
STATES = ["Virginia", "Texas", "Washington", "North Carolina", "Colorado", "Arizona"]
COUNTRIES = ["United States", "Canada", "United Kingdom", "Germany", "Australia"]
COMPANIES = [
    "Northstar Analytics",
    "Apex Systems",
    "Summit Retail",
    "Harbor Financial",
    "Keystone Health",
]
JOBS = ["Data Engineer", "Analyst", "Manager", "Developer", "Architect"]


class FallbackFaker:
    """Small deterministic fallback for environments without Faker."""

    def __init__(self, random_gen: random.Random):
        self.random = random_gen

    def seed_instance(self, seed: int) -> None:
        self.random.seed(seed)

    def first_name(self) -> str:
        return self.random.choice(FIRST_NAMES)

    def last_name(self) -> str:
        return self.random.choice(LAST_NAMES)

    def name(self) -> str:
        return f"{self.first_name()} {self.last_name()}"

    def user_name(self) -> str:
        return f"{self.first_name()}.{self.last_name()}".lower()

    def phone_number(self) -> str:
        return f"+1-555-{self.random.randint(1000, 9999):04d}"

    def street_address(self) -> str:
        return f"{self.random.randint(100, 9999)} {self.random.choice(STREET_NAMES)}"

    def city(self) -> str:
        return self.random.choice(CITIES)

    def state(self) -> str:
        return self.random.choice(STATES)

    def postcode(self) -> str:
        return f"{self.random.randint(10000, 99999):05d}"

    def country(self) -> str:
        return self.random.choice(COUNTRIES)

    def company(self) -> str:
        return self.random.choice(COMPANIES)

    def job(self) -> str:
        return self.random.choice(JOBS)

    def date_between(self, start_date: str | date = "-10y", end_date: str | date = "today") -> date:
        start = _fallback_date(start_date, date(2016, 1, 1))
        end = _fallback_date(end_date, date(2026, 1, 1))
        delta = max(0, (end - start).days)
        return start + timedelta(days=self.random.randint(0, delta))


def stable_seed(seed: int | None, salt: str = "") -> int | None:
    """Return a deterministic Faker-friendly seed for a seed/salt pair."""

    if seed is None:
        return None
    digest = hashlib.sha256(f"{seed}:{salt}".encode()).hexdigest()
    return int(digest[:16], 16) % (2**32)


@dataclass(frozen=True)
class PersonRecord:
    first_name: str
    last_name: str
    full_name: str
    email: str


class RealisticValueGenerator:
    """Small wrapper around Faker with deterministic enterprise-friendly helpers."""

    def __init__(self, seed: int | None = None, locale: str = "en_US"):
        self.seed = seed
        self.locale = locale
        resolved_seed = stable_seed(seed, locale)
        self.random = random.Random(resolved_seed)
        self.fake = (
            FAKER_FACTORY(locale) if FAKER_FACTORY is not None else FallbackFaker(self.random)
        )
        if resolved_seed is not None:
            self.fake.seed_instance(resolved_seed)

    def child(self, salt: str) -> RealisticValueGenerator:
        """Create an independent deterministic child generator."""

        return RealisticValueGenerator(seed=stable_seed(self.seed, salt), locale=self.locale)

    def person_record(self) -> PersonRecord:
        first_name = self.first_name()
        last_name = self.last_name()
        return PersonRecord(
            first_name=first_name,
            last_name=last_name,
            full_name=f"{first_name} {last_name}",
            email=self.email(first_name=first_name, last_name=last_name),
        )

    def person_name(self) -> str:
        return self.fake.name()

    def first_name(self) -> str:
        return self.fake.first_name()

    def last_name(self) -> str:
        return self.fake.last_name()

    def email(self, first_name: str | None = None, last_name: str | None = None) -> str:
        if first_name and last_name:
            prefix = f"{_slug(first_name)}.{_slug(last_name)}"
        else:
            prefix = _slug(self.fake.user_name())
        suffix = self.random.randint(100, 9999)
        return f"{prefix}{suffix}@example.com"

    def phone_number(self) -> str:
        return self.fake.phone_number()

    def street_address(self) -> str:
        return self.fake.street_address()

    def city(self) -> str:
        return self.fake.city()

    def state(self) -> str:
        return self.fake.state()

    def zip_code(self) -> str:
        return self.fake.postcode()

    def country(self) -> str:
        return self.fake.country()

    def company_name(self) -> str:
        return self.fake.company()

    def job_title(self) -> str:
        return self.fake.job()

    def date_between(self, start_date: str | date = "-10y", end_date: str | date = "today") -> date:
        return self.fake.date_between(start_date=start_date, end_date=end_date)

    def random_choice(self, values: list[Any] | tuple[Any, ...]) -> Any:
        if not values:
            raise ValueError("random_choice requires at least one value.")
        return self.random.choice(list(values))

    def random_amount(self, min_value: float, max_value: float, decimals: int = 2) -> float:
        return round(self.random.uniform(min_value, max_value), decimals)

    def random_decimal(self, min_value: float, max_value: float, decimals: int = 2) -> Decimal:
        return Decimal(str(self.random_amount(min_value, max_value, decimals)))

    def random_int(self, min_value: int, max_value: int) -> int:
        return self.random.randint(min_value, max_value)

    def random_ints(self, rows: int, min_value: int, max_value: int) -> list[int]:
        return [self.random_int(min_value, max_value) for _ in range(rows)]

    def random_bool(self) -> bool:
        return self.random.random() < 0.5


def maybe_null(value: Any, null_probability: float, random_gen: random.Random) -> Any:
    """Return ``None`` with the requested probability, otherwise return ``value``."""

    if random_gen.random() < null_probability:
        return None
    return value


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", ".", value.strip().lower())
    cleaned = cleaned.strip(".")
    return cleaned or "user"


def _fallback_date(value: str | date, default: date) -> date:
    if isinstance(value, date):
        return value
    if value == "today":
        return date(2026, 1, 1)
    if isinstance(value, str) and value.endswith("y") and value.startswith("-"):
        return date(2026 + int(value[:-1]), 1, 1)
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return default
