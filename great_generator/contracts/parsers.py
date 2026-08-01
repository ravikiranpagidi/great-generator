"""Small parser abstraction for contract ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from great_generator.contracts.diagnostics import ContractDiagnostic
from great_generator.schemas.models import ContractSchema


@dataclass(frozen=True)
class ParseResult:
    """Result returned by a contract parser."""

    contract: ContractSchema
    diagnostics: tuple[ContractDiagnostic, ...]
    source_format: str
    dialect: str | None = None

    @property
    def warnings(self) -> tuple[ContractDiagnostic, ...]:
        return tuple(item for item in self.diagnostics if item.severity == "warning")

    @property
    def errors(self) -> tuple[ContractDiagnostic, ...]:
        return tuple(item for item in self.diagnostics if item.severity == "error")


class ContractParser(Protocol):
    """Protocol for parsers that produce canonical contracts."""

    source_format: str

    def parse(
        self,
        source: str,
        *,
        dialect: str | None = None,
        strict: bool = True,
        name: str = "contract",
    ) -> ParseResult:
        """Parse source into a canonical contract."""
