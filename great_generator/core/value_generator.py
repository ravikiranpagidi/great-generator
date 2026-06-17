"""Faker-backed realistic value generation primitives."""

from __future__ import annotations

import hashlib
import random
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from faker import Faker


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
        self.fake = Faker(locale)
        resolved_seed = stable_seed(seed, locale)
        if resolved_seed is not None:
            self.fake.seed_instance(resolved_seed)
        self.random = random.Random(resolved_seed)

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

    def company_name(self) -> str:
        return self.fake.company()

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


def maybe_null(value: Any, null_probability: float, random_gen: random.Random) -> Any:
    """Return ``None`` with the requested probability, otherwise return ``value``."""

    if random_gen.random() < null_probability:
        return None
    return value


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", ".", value.strip().lower())
    cleaned = cleaned.strip(".")
    return cleaned or "user"
