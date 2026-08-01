"""Structured diagnostics for contract ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SourceLocation:
    """Best-effort source location reported by a parser."""

    line: int | None = None
    column: int | None = None
    start: int | None = None
    end: int | None = None

    def to_dict(self) -> dict[str, int | None]:
        return {
            "line": self.line,
            "column": self.column,
            "start": self.start,
            "end": self.end,
        }


@dataclass(frozen=True)
class ContractDiagnostic:
    """A warning or error produced while parsing a contract source."""

    statement: str
    dialect: str | None
    construct: str
    message: str
    severity: str = "warning"
    table: str | None = None
    column: str | None = None
    location: SourceLocation | None = None
    recommendation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "statement": self.statement,
            "dialect": self.dialect,
            "construct": self.construct,
            "message": self.message,
            "severity": self.severity,
            "table": self.table,
            "column": self.column,
            "location": self.location.to_dict() if self.location else None,
            "recommendation": self.recommendation,
        }


class ContractParseError(ValueError):
    """Raised when a contract source cannot be parsed safely."""

    def __init__(
        self, message: str, diagnostics: list[ContractDiagnostic] | tuple[ContractDiagnostic, ...]
    ):
        self.diagnostics = tuple(diagnostics)
        details = "; ".join(diagnostic.message for diagnostic in self.diagnostics[:3])
        suffix = f" Details: {details}" if details else ""
        super().__init__(message + suffix)
