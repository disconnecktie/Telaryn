"""Verify OpenAI requests remain structured, concise, and output-bounded."""

import json

from app.ai.context import WorkContext
from app.schemas.work_intake import WorkIntakeSnapshot
from app.ai import openai_provider


class _FakeResponse:
    def __init__(self, output_text: str):
        self.output_text = output_text


class _FakeResponses:
    def __init__(self):
        self.options = None

    def create(self, **options):
        self.options = options
        additions = [
            {"text": f"Criterion {index}", "basis": "inferred"}
            for index in range(6)
        ]
        revisions = [
            {
                "source_index": 0,
                "suggested_text": f"Revision {index}",
                "rationale": "Make the outcome measurable.",
                "basis": "inferred",
            }
            for index in range(6)
        ]
        return _FakeResponse(json.dumps({
            "suggested_title": None,
            "suggested_description": None,
            "suggested_priority": None,
            "suggested_ticket_type": None,
            "reasoning_summary": "Concise review.",
            "missing_information": [],
            "recommendations": [],
            "acceptance_criteria": additions,
            "suggested_subtasks": [],
            "subtask_revisions": [],
            "acceptance_criteria_revisions": revisions,
        }))


class _FakeOpenAI:
    def __init__(self, **options):
        self.options = options
        self.responses = _FakeResponses()


def test_openai_review_is_schema_constrained_concise_and_bounded(monkeypatch):
    monkeypatch.setattr(openai_provider, "OpenAI", _FakeOpenAI)
    provider = openai_provider.OpenAIProvider(
        api_key="test-key",
        model="test-model",
        timeout_seconds=45,
        max_output_tokens=3500,
        reasoning_effort="low",
    )

    result = provider.review_ticket(
        WorkContext(
            title="Review a structured ticket",
            description=None,
            project_name=None,
            status="ready",
            priority="medium",
            ticket_type="task",
        )
    )

    options = provider.client.responses.options
    assert options["reasoning"] == {"effort": "low"}
    assert options["store"] is False
    assert options["max_output_tokens"] == 3500
    assert options["text"]["verbosity"] == "low"
    assert options["text"]["format"]["type"] == "json_schema"
    assert options["text"]["format"]["strict"] is True
    assert len(result.acceptance_criteria) == 5
    assert result.acceptance_criteria[0].basis.value == "inferred"
    assert len(result.acceptance_criteria_revisions) == 5


class _FakeWorkIntakeResponses:
    def __init__(self):
        self.options = None

    def create(self, **options):
        self.options = options
        return _FakeResponse(json.dumps({
            "action": "needs_clarification",
            "summary": "More context is needed.",
            "rationale": "The request does not identify a bounded outcome.",
            "confidence": "low",
            "target_project_id": None,
            "target_ticket_id": None,
            "proposed_project": None,
            "proposed_tickets": [],
            "proposed_ticket_changes": None,
            "questions": ["What outcome should this work achieve?"],
            "is_provisional": True,
            "clarification_prompt": "Answer one focused question to improve this proposal.",
        }))


def _assert_openai_strict_objects(schema):
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            assert schema.get("additionalProperties") is False
            assert set(schema.get("required", [])) == set(schema.get("properties", {}))
        for value in schema.values():
            _assert_openai_strict_objects(value)
    elif isinstance(schema, list):
        for value in schema:
            _assert_openai_strict_objects(value)


def test_work_intake_uses_a_fully_required_strict_provider_schema(monkeypatch):
    monkeypatch.setattr(openai_provider, "OpenAI", _FakeOpenAI)
    provider = openai_provider.OpenAIProvider(
        api_key="test-key",
        model="test-model",
        timeout_seconds=45,
        max_output_tokens=3500,
        reasoning_effort="low",
    )
    provider.client.responses = _FakeWorkIntakeResponses()

    result = provider.propose_work_intake(
        WorkIntakeSnapshot(source_text="Help shape this work", projects=[], tickets=[])
    )

    options = provider.client.responses.options
    schema = options["text"]["format"]["schema"]
    _assert_openai_strict_objects(schema)
    assert options["store"] is False
    assert result.action == "needs_clarification"
    assert result.questions == ["What outcome should this work achieve?"]


def test_work_intake_instructions_make_structure_scope_driven():
    instructions = openai_provider.WORK_INTAKE_INSTRUCTIONS

    assert "Choose each count from the actual scope" in instructions
    assert "Acceptance criteria describe independently verifiable completion outcomes" in instructions
    assert "Subtasks describe concrete actions" in instructions
    assert "they are not slots to fill" in instructions
    assert "Do not add an item merely to represent a label" in instructions


class _FakeOversizedWorkIntakeResponses:
    def create(self, **options):
        ticket = {
            "title": "Bounded deliverable",
            "description": None,
            "priority": "medium",
            "ticket_type": "task",
            "project_id": None,
            "acceptance_criteria": [
                {"text": f"Criterion {index}", "basis": "inferred"}
                for index in range(8)
            ],
            "subtasks": [
                {"text": f"Subtask {index}", "basis": "recommended"}
                for index in range(8)
            ],
        }
        return _FakeResponse(json.dumps({
            "action": "create_tickets",
            "summary": "Split the work.",
            "rationale": "The source contains multiple deliverables.",
            "confidence": "medium",
            "target_project_id": None,
            "target_ticket_id": None,
            "proposed_project": None,
            "proposed_tickets": [ticket for _ in range(9)],
            "proposed_ticket_changes": None,
            "questions": [f"Question {index}?" for index in range(7)],
            "is_provisional": True,
            "clarification_prompt": "Answer what you can to improve this proposal.",
        }))


def test_work_intake_safely_bounds_valid_provider_lists(monkeypatch):
    monkeypatch.setattr(openai_provider, "OpenAI", _FakeOpenAI)
    provider = openai_provider.OpenAIProvider(
        api_key="test-key",
        model="test-model",
        timeout_seconds=45,
        max_output_tokens=3500,
        reasoning_effort="low",
    )
    provider.client.responses = _FakeOversizedWorkIntakeResponses()

    result = provider.propose_work_intake(
        WorkIntakeSnapshot(source_text="Plan several deliverables", projects=[], tickets=[])
    )

    assert len(result.proposed_tickets) == 8
    assert len(result.questions) == 5
    assert all(len(ticket.acceptance_criteria) == 7 for ticket in result.proposed_tickets)
    assert all(len(ticket.subtasks) == 7 for ticket in result.proposed_tickets)
