"""Pydantic schemas + LangGraph TypedDict state for the contract analysis workflow."""
from __future__ import annotations

import operator
from typing import Annotated, Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


RiskLevel = Literal["Critical", "High", "Medium", "Low", "Info"]
RiskCategory = Literal[
    "Legal", "Financial", "IP", "Compliance", "Operational",
    "Privacy", "Termination", "Liability", "Other",
]

RISK_WEIGHTS: Dict[str, float] = {
    "Critical": 1.0, "High": 0.7, "Medium": 0.4, "Low": 0.15, "Info": 0.05,
}


class ContractInfo(BaseModel):
    contract_type: str = Field(description="E.g. Employment Contract, NDA, SaaS Agreement")
    industry: Optional[str] = None
    governing_law: Optional[str] = None
    effective_date: Optional[str] = None
    parties: List[str] = Field(default_factory=list)
    summary: str = ""


class Party(BaseModel):
    name: str
    role: str
    address: Optional[str] = None
    entity_type: Optional[str] = None


class FinancialTerm(BaseModel):
    label: str
    amount: Optional[str] = None
    currency: Optional[str] = "USD"
    cadence: Optional[str] = None
    notes: Optional[str] = None


class KeyDate(BaseModel):
    label: str
    date_text: str
    iso_date: Optional[str] = None


class Obligation(BaseModel):
    party: str
    obligation: str
    deadline: Optional[str] = None


class EntityExtraction(BaseModel):
    parties: List[Party] = Field(default_factory=list)
    financial_terms: List[FinancialTerm] = Field(default_factory=list)
    key_dates: List[KeyDate] = Field(default_factory=list)
    obligations: List[Obligation] = Field(default_factory=list)


class Modification(BaseModel):
    original_text: str
    suggested_text: str
    reason: str
    risk_level: RiskLevel = "Medium"
    confidence: float = Field(default=0.7, ge=0, le=1)


class RiskFinding(BaseModel):
    title: str
    description: str
    category: RiskCategory
    risk_level: RiskLevel
    section_reference: Optional[str] = None
    recommendation: str = ""
    confidence: float = Field(default=0.7, ge=0, le=1)


class ComplianceFinding(BaseModel):
    framework: str
    requirement: str
    status: Literal["Compliant", "Partial", "Non-Compliant", "Not Applicable"]
    explanation: str
    recommendation: Optional[str] = None


class MissingClause(BaseModel):
    clause_title: str
    importance: RiskLevel
    why_missing_matters: str
    suggested_text: str


class Conflict(BaseModel):
    section_a: str
    section_b: str
    description: str
    risk_level: RiskLevel
    resolution: str


class PIIFinding(BaseModel):
    type: str
    excerpt: str
    recommendation: str


class StepAnalysis(BaseModel):
    role: str = ""
    analysis: str
    modifications: List[Modification] = Field(default_factory=list)
    risk_findings: List[RiskFinding] = Field(default_factory=list)


class ReviewPlan(BaseModel):
    roles: List[str]


class ClauseCheckSummary(BaseModel):
    clause_title: str
    analysis: str


class ContractReviewState(TypedDict, total=False):
    contract_text: str
    primary_objective: str
    specific_focus: Optional[str]
    sections_split: List[Dict[str, Any]]

    contract_info: ContractInfo
    entities: EntityExtraction
    pii_findings: List[PIIFinding]
    expected_clauses: List[str]
    retrieved_clauses: List[Dict[str, Any]]

    clause_check_results: Annotated[List[Dict[str, Any]], operator.add]
    missing_clauses: List[MissingClause]
    conflicts: List[Conflict]
    compliance_findings: List[ComplianceFinding]
    review_plan: ReviewPlan
    role_analyses: Annotated[List[StepAnalysis], operator.add]

    modifications: Annotated[List[Modification], operator.add]
    risk_findings: Annotated[List[RiskFinding], operator.add]

    overall_risk_score: float
    overall_risk_level: RiskLevel

    final_report_md: str
    final_report_json: Dict[str, Any]

    # Per-fanout instance fields (populated by Send payloads only)
    clause: Dict[str, Any]
    role: str

    errors: Annotated[List[str], operator.add]


def aggregate_risk(findings: List[RiskFinding]) -> tuple[float, RiskLevel]:
    if not findings:
        return 0.0, "Low"
    score = sum(RISK_WEIGHTS.get(f.risk_level, 0.4) * f.confidence for f in findings) / max(len(findings), 1)
    level: RiskLevel = (
        "Critical" if score >= 0.75 else
        "High" if score >= 0.55 else
        "Medium" if score >= 0.3 else
        "Low"
    )
    return round(score, 3), level
