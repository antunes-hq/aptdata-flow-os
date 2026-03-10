"""Business rules registry with audit logging."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class RuleStatus(str, Enum):
    """Execution status of a business rule application."""

    APPLIED = "APPLIED"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


@dataclass
class BusinessRule:
    """Declaration of a single business rule.

    Parameters
    ----------
    rule_id:
        Unique identifier (e.g. ``"BR-001"``).
    name:
        Human-readable rule name.
    version:
        Semantic version string (e.g. ``"1.0.0"``).
    owner:
        Team or person responsible for this rule.
    description:
        Detailed description of what the rule enforces.
    expression:
        Human-readable expression or pseudo-code representing the rule logic.
    tags:
        Free-form classification tags.
    effective_from:
        ISO-8601 date/time from which the rule is effective.
    effective_until:
        ISO-8601 date/time after which the rule expires (empty = no expiry).
    metadata:
        Arbitrary extra metadata.
    """

    rule_id: str
    name: str
    version: str = "1.0.0"
    owner: str = ""
    description: str = ""
    expression: str = ""
    tags: list[str] = field(default_factory=list)
    effective_from: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    effective_until: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleAuditEntry:
    """Audit record for a single rule application.

    Parameters
    ----------
    rule_id:
        ID of the rule that was applied.
    rule_version:
        Version of the rule that was applied.
    status:
        Outcome of the rule execution.
    workflow_name:
        Workflow in which the rule was executed.
    step_name:
        Step within the workflow.
    trace_id:
        OpenTelemetry trace identifier.
    timestamp:
        UTC ISO-8601 timestamp of the audit entry.
    rows_affected:
        Number of rows affected by the rule.
    details:
        Human-readable summary of what the rule did.
    metadata:
        Arbitrary extra metadata.
    """

    rule_id: str
    rule_version: str = "1.0.0"
    status: RuleStatus = RuleStatus.APPLIED
    workflow_name: str = ""
    step_name: str = ""
    trace_id: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    rows_affected: int = 0
    details: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class RuleRegistry:
    """In-memory registry for :class:`BusinessRule` definitions and audit logs.

    Examples
    --------
    ::

        registry = RuleRegistry()
        registry.register(BusinessRule(rule_id="BR-001", name="Age must be positive"))
        rule = registry.get("BR-001")
        rules = registry.list_rules(tag="finance")
    """

    def __init__(self) -> None:
        self._rules: dict[str, BusinessRule] = {}
        self._audit_log: list[RuleAuditEntry] = []

    def register(self, rule: BusinessRule) -> None:
        """Register *rule* under its :attr:`~BusinessRule.rule_id`."""
        self._rules[rule.rule_id] = rule

    def get(self, rule_id: str) -> BusinessRule | None:
        """Return the rule with *rule_id*, or ``None`` if not found."""
        return self._rules.get(rule_id)

    def list_rules(
        self,
        owner: str | None = None,
        tag: str | None = None,
    ) -> list[BusinessRule]:
        """Return all registered rules, optionally filtered by *owner* or *tag*.

        Parameters
        ----------
        owner:
            If provided, only rules owned by this owner are returned.
        tag:
            If provided, only rules with this tag are returned.
        """
        results = list(self._rules.values())
        if owner is not None:
            results = [r for r in results if r.owner == owner]
        if tag is not None:
            results = [r for r in results if tag in r.tags]
        return results

    def record_audit(self, entry: RuleAuditEntry) -> None:
        """Append *entry* to the audit log."""
        self._audit_log.append(entry)

    def get_audit_log(
        self,
        rule_id: str | None = None,
        trace_id: str | None = None,
    ) -> list[RuleAuditEntry]:
        """Return audit entries, optionally filtered by *rule_id* or *trace_id*.

        Parameters
        ----------
        rule_id:
            If provided, only entries for this rule are returned.
        trace_id:
            If provided, only entries with this trace ID are returned.
        """
        entries = list(self._audit_log)
        if rule_id is not None:
            entries = [e for e in entries if e.rule_id == rule_id]
        if trace_id is not None:
            entries = [e for e in entries if e.trace_id == trace_id]
        return entries


__all__ = [
    "RuleStatus",
    "BusinessRule",
    "RuleAuditEntry",
    "RuleRegistry",
]
