import logging
from time import perf_counter

from sqlalchemy.orm import Session

from app.database.models import Finding, RuleExecution, utc_now
from app.rules.context import RuleContext
from app.rules.registry import registered_rules

logger = logging.getLogger(__name__)


class RuleEngine:
    def __init__(self, rules=None) -> None:
        self.rules = rules if rules is not None else registered_rules()

    def execute(self, context: RuleContext) -> tuple[list[Finding], list[RuleExecution]]:
        findings: list[Finding] = []
        executions: list[RuleExecution] = []
        for rule in self.rules:
            started = perf_counter()
            resolved = (context.rule_configurations or {}).get(rule.code, {})
            configuration = dict(resolved.get("configuration", {}))
            execution = RuleExecution(
                analysis_run_id=context.analysis_run.id,
                rule_code=rule.code,
                rule_name=rule.name,
                status="running",
                evaluated_records=len(context.transactions),
                started_at=utc_now(),
                rule_version=str(resolved.get("version", rule.version)),
                configuration_snapshot_json=configuration,
            )
            context.session.add(execution)
            if resolved and not resolved.get("enabled", True):
                execution.status = "skipped"
                execution.findings_generated = 0
                execution.skip_reason = "Rule disabled"
                execution.execution_time_ms = max(1, round((perf_counter() - started) * 1000))
                execution.completed_at = utc_now()
                executions.append(execution)
                continue
            try:
                candidates = rule.evaluate(context)
                generated = [
                    Finding(
                        analysis_run_id=context.analysis_run.id,
                        transaction_id=candidate.transaction_id,
                        rule_code=rule.code,
                        title=candidate.title,
                        description=candidate.description,
                        category=candidate.category,
                        severity=candidate.severity,
                        status="open",
                        detected_value=candidate.detected_value,
                        expected_value=candidate.expected_value,
                        deviation_percentage=candidate.deviation_percentage,
                        estimated_impact=candidate.estimated_impact,
                        confidence_score=candidate.confidence_score,
                        evidence_json=candidate.evidence,
                    )
                    for candidate in candidates
                ]
                context.session.add_all(generated)
                findings.extend(generated)
                execution.status = "completed"
                execution.findings_generated = len(generated)
            except Exception as exc:  # Rule isolation boundary.
                logger.exception("Rule %s failed for run %s", rule.code, context.analysis_run.id)
                execution.status = "failed"
                execution.error_message = "Rule evaluation failed."
            finally:
                execution.execution_time_ms = max(1, round((perf_counter() - started) * 1000))
                execution.completed_at = utc_now()
                executions.append(execution)
        context.session.flush()
        context.analysis_run.findings_count = len(findings)
        return findings, executions


rule_engine = RuleEngine()
