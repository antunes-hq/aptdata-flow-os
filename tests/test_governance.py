"""Tests for governance plugin — rules, catalog, classification, lineage_store."""

from __future__ import annotations


from smart_data.plugins.governance.catalog import DatasetCatalog, DatasetCatalogEntry
from smart_data.plugins.governance.classification import (
    ColumnClassification,
    DataClassificationPolicy,
)
from smart_data.plugins.governance.lineage_store import LineageStore
from smart_data.plugins.governance.rules import (
    BusinessRule,
    RuleAuditEntry,
    RuleRegistry,
    RuleStatus,
)
from smart_data.plugins.quality.contract import SchemaContract


# ---------------------------------------------------------------------------
# BusinessRule & RuleRegistry
# ---------------------------------------------------------------------------


class TestBusinessRule:
    def test_defaults(self) -> None:
        rule = BusinessRule(rule_id="BR-001", name="Age must be positive")
        assert rule.rule_id == "BR-001"
        assert rule.version == "1.0.0"
        assert rule.tags == []
        assert rule.expression == ""

    def test_custom_values(self) -> None:
        rule = BusinessRule(
            rule_id="BR-002",
            name="Revenue positive",
            owner="finance",
            tags=["finance", "revenue"],
            expression="revenue > 0",
        )
        assert rule.owner == "finance"
        assert "finance" in rule.tags


class TestRuleRegistry:
    def test_register_and_get(self) -> None:
        registry = RuleRegistry()
        rule = BusinessRule(rule_id="BR-001", name="Test Rule")
        registry.register(rule)
        assert registry.get("BR-001") is rule

    def test_get_missing_returns_none(self) -> None:
        registry = RuleRegistry()
        assert registry.get("nonexistent") is None

    def test_list_rules_all(self) -> None:
        registry = RuleRegistry()
        registry.register(BusinessRule(rule_id="BR-001", name="R1"))
        registry.register(BusinessRule(rule_id="BR-002", name="R2"))
        rules = registry.list_rules()
        assert len(rules) == 2

    def test_list_rules_filter_owner(self) -> None:
        registry = RuleRegistry()
        registry.register(BusinessRule(rule_id="BR-001", name="R1", owner="alice"))
        registry.register(BusinessRule(rule_id="BR-002", name="R2", owner="bob"))
        result = registry.list_rules(owner="alice")
        assert len(result) == 1
        assert result[0].rule_id == "BR-001"

    def test_list_rules_filter_tag(self) -> None:
        registry = RuleRegistry()
        registry.register(BusinessRule(rule_id="BR-001", name="R1", tags=["pii", "gdpr"]))
        registry.register(BusinessRule(rule_id="BR-002", name="R2", tags=["finance"]))
        result = registry.list_rules(tag="pii")
        assert len(result) == 1

    def test_list_rules_filter_owner_and_tag(self) -> None:
        registry = RuleRegistry()
        registry.register(BusinessRule(rule_id="BR-001", name="R1", owner="alice", tags=["pii"]))
        registry.register(BusinessRule(rule_id="BR-002", name="R2", owner="alice", tags=["finance"]))
        result = registry.list_rules(owner="alice", tag="pii")
        assert len(result) == 1

    def test_record_audit(self) -> None:
        registry = RuleRegistry()
        entry = RuleAuditEntry(rule_id="BR-001", status=RuleStatus.APPLIED)
        registry.record_audit(entry)
        log = registry.get_audit_log()
        assert len(log) == 1

    def test_get_audit_log_filter_rule_id(self) -> None:
        registry = RuleRegistry()
        registry.record_audit(RuleAuditEntry(rule_id="BR-001"))
        registry.record_audit(RuleAuditEntry(rule_id="BR-002"))
        log = registry.get_audit_log(rule_id="BR-001")
        assert len(log) == 1
        assert log[0].rule_id == "BR-001"

    def test_get_audit_log_filter_trace_id(self) -> None:
        registry = RuleRegistry()
        registry.record_audit(RuleAuditEntry(rule_id="BR-001", trace_id="trace-abc"))
        registry.record_audit(RuleAuditEntry(rule_id="BR-001", trace_id="trace-xyz"))
        log = registry.get_audit_log(trace_id="trace-abc")
        assert len(log) == 1
        assert log[0].trace_id == "trace-abc"

    def test_rule_audit_defaults(self) -> None:
        entry = RuleAuditEntry(rule_id="BR-001")
        assert entry.status == RuleStatus.APPLIED
        assert entry.rows_affected == 0

    def test_rule_status_values(self) -> None:
        assert set(RuleStatus) == {RuleStatus.APPLIED, RuleStatus.SKIPPED, RuleStatus.FAILED}


# ---------------------------------------------------------------------------
# DatasetCatalog
# ---------------------------------------------------------------------------


class TestDatasetCatalog:
    def test_register_and_get(self) -> None:
        catalog = DatasetCatalog()
        entry = DatasetCatalogEntry(uri="s3://bucket/data.parquet", name="Sales")
        catalog.register(entry)
        retrieved = catalog.get("s3://bucket/data.parquet")
        assert retrieved is entry

    def test_get_missing_returns_none(self) -> None:
        catalog = DatasetCatalog()
        assert catalog.get("nonexistent") is None

    def test_register_replaces_existing(self) -> None:
        catalog = DatasetCatalog()
        catalog.register(DatasetCatalogEntry(uri="s3://bucket/a", name="Original"))
        catalog.register(DatasetCatalogEntry(uri="s3://bucket/a", name="Replaced"))
        assert catalog.get("s3://bucket/a").name == "Replaced"

    def test_list_entries(self) -> None:
        catalog = DatasetCatalog()
        catalog.register(DatasetCatalogEntry(uri="s3://a"))
        catalog.register(DatasetCatalogEntry(uri="s3://b"))
        assert len(catalog.list_entries()) == 2

    def test_search_by_owner(self) -> None:
        catalog = DatasetCatalog()
        catalog.register(DatasetCatalogEntry(uri="s3://a", owner="alice"))
        catalog.register(DatasetCatalogEntry(uri="s3://b", owner="bob"))
        results = catalog.search(owner="alice")
        assert len(results) == 1
        assert results[0].uri == "s3://a"

    def test_search_by_tag(self) -> None:
        catalog = DatasetCatalog()
        catalog.register(DatasetCatalogEntry(uri="s3://a", tags=["pii", "gdpr"]))
        catalog.register(DatasetCatalogEntry(uri="s3://b", tags=["finance"]))
        results = catalog.search(tag="pii")
        assert len(results) == 1

    def test_search_by_classification(self) -> None:
        catalog = DatasetCatalog()
        catalog.register(DatasetCatalogEntry(uri="s3://a", classification=ColumnClassification.PII))
        catalog.register(DatasetCatalogEntry(uri="s3://b", classification=ColumnClassification.PUBLIC))
        results = catalog.search(classification=ColumnClassification.PII)
        assert len(results) == 1

    def test_search_combined_filters(self) -> None:
        catalog = DatasetCatalog()
        catalog.register(
            DatasetCatalogEntry(uri="s3://a", owner="alice", tags=["pii"])
        )
        catalog.register(
            DatasetCatalogEntry(uri="s3://b", owner="alice", tags=["finance"])
        )
        results = catalog.search(owner="alice", tag="pii")
        assert len(results) == 1

    def test_entry_with_schema_contract(self) -> None:
        contract = SchemaContract(name="my_contract")
        entry = DatasetCatalogEntry(uri="s3://a", schema_contract=contract)
        assert entry.schema_contract.name == "my_contract"


# ---------------------------------------------------------------------------
# DataClassificationPolicy
# ---------------------------------------------------------------------------


class TestDataClassificationPolicy:
    def test_defaults(self) -> None:
        policy = DataClassificationPolicy(name="PII Policy")
        assert policy.pii_columns == []
        assert policy.retention_days == 0
        assert policy.encryption_required is False
        assert policy.access_roles == []

    def test_custom_values(self) -> None:
        policy = DataClassificationPolicy(
            name="GDPR Policy",
            pii_columns=["email", "phone"],
            retention_days=365,
            encryption_required=True,
            access_roles=["data-engineers", "privacy-team"],
        )
        assert "email" in policy.pii_columns
        assert policy.retention_days == 365
        assert policy.encryption_required is True

    def test_column_classification_re_export(self) -> None:
        from smart_data.plugins.governance.classification import ColumnClassification

        assert ColumnClassification.PII == "PII"


# ---------------------------------------------------------------------------
# LineageStore
# ---------------------------------------------------------------------------


class TestLineageStore:
    def test_save_and_load(self) -> None:
        from smart_data.core.lineage import LineageGraph

        store = LineageStore()
        graph = LineageGraph(run_id="run-1", workflow_name="wf")
        store.save(graph)
        loaded = store.load("run-1")
        assert loaded is graph

    def test_load_missing_returns_none(self) -> None:
        store = LineageStore()
        assert store.load("nonexistent") is None

    def test_list_runs_sorted(self) -> None:
        from smart_data.core.lineage import LineageGraph

        store = LineageStore()
        store.save(LineageGraph(run_id="run-c", workflow_name="wf"))
        store.save(LineageGraph(run_id="run-a", workflow_name="wf"))
        store.save(LineageGraph(run_id="run-b", workflow_name="wf"))
        assert store.list_runs() == ["run-a", "run-b", "run-c"]

    def test_query_by_dataset(self) -> None:
        from smart_data.core.lineage import LineageEventType, LineageGraph, LineageNode

        store = LineageStore()
        graph1 = LineageGraph(run_id="run-1", workflow_name="wf")
        graph1.add_node(LineageNode(dataset_uri="s3://bucket/a", event_type=LineageEventType.READ))

        graph2 = LineageGraph(run_id="run-2", workflow_name="wf")
        graph2.add_node(LineageNode(dataset_uri="s3://bucket/b", event_type=LineageEventType.READ))

        store.save(graph1)
        store.save(graph2)

        results = store.query_by_dataset("s3://bucket/a")
        assert len(results) == 1
        assert results[0].run_id == "run-1"

    def test_query_by_dataset_no_match(self) -> None:
        store = LineageStore()
        assert store.query_by_dataset("nonexistent") == []

    def test_save_overwrites_run(self) -> None:
        from smart_data.core.lineage import LineageGraph

        store = LineageStore()
        store.save(LineageGraph(run_id="run-1", workflow_name="old"))
        store.save(LineageGraph(run_id="run-1", workflow_name="new"))
        assert store.load("run-1").workflow_name == "new"
