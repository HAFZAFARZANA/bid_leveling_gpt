"""Takeoff Pydantic schemas and data contracts."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProjectMetadata(BaseModel):
    """Project-level administrative and bidding metadata."""

    project_name: Optional[str] = Field(
        None,
        description="Identified project or building name",
        example="450 Lexington Ave Sprinkler Upgrade",
    )
    location: Optional[str] = Field(
        None,
        description="Project site address or city/state",
        example="New York, NY",
    )
    bid_date: Optional[str] = Field(
        None,
        description="Bid submission or proposal date",
        example="2026-10-12",
    )
    budget: Optional[float] = Field(
        None,
        description="Total bid budget or price if stated in document",
        example=485000.0,
    )
    target_budget: Optional[float] = Field(
        None,
        description="Target budget or owner allowance if explicitly specified",
        example=500000.0,
    )
    prepared_by: Optional[str] = Field(
        None,
        description="Contractor, subcontractor (e.g., NYM Fire Protection), or estimator name",
        example="NYM Fire Protection Inc.",
    )
    trade: Optional[str] = Field(
        None,
        description="Identified construction trade, e.g. HVAC, Electrical, Fire Alarm, Sprinkler, Plumbing, etc.",
        example="Electrical",
    )


class TakeoffItem(BaseModel):
    """Individual extracted sprinkler or construction takeoff line item."""

    item_number: Optional[str] = Field(
        None,
        description="Original item number, line identifier, or code from source (e.g., '1.01', 'FP-1', 'A')",
        example="1.01",
    )
    section: str = Field(
        ...,
        description="Dynamic section key assigned from the source document; no fixed trade taxonomy is required.",
        example="equipment_schedule",
    )
    original_description: str = Field(
        ...,
        description="Verbatim or original source description of the scope item",
        example="Semi-Recessed Pendent Sprinkler Heads - Chrome Finish",
    )
    model_number: Optional[str] = Field(None, description="Equipment model or manufacturer part number exactly as shown in the source")
    item_code: Optional[str] = Field(None, description="Source item code or SKU, if explicitly stated")
    quantity: Optional[float] = Field(
        None,
        description="Contractor's stated quantity (NYM QTY). null if not explicitly stated in document. NEVER assumed to be 1.",
        example=350.0,
    )
    unit: Optional[str] = Field(
        None,
        description="Unit of measure (e.g., 'EA', 'LFT', 'SQ FT', 'LS', 'FLR'). null if not specified.",
        example="EA",
    )
    source_page: Optional[int] = Field(
        None,
        description="1-indexed source PDF page number, or null if it cannot be verified",
        example=1,
    )
    source_evidence: Optional[str] = Field(
        None,
        description="Short source excerpt confirming this item, or null if unavailable",
        example="Equipment schedule: 64 units",
    )
    review_required: bool = Field(
        default=False,
        description="Flagged true if item has missing quantity, ambiguous unit, vague description, or possible duplicate",
        example=False,
    )
    review_reasons: List[str] = Field(
        default_factory=list,
        description="List of specific reasons why estimator review is required",
        example=[],
    )
    approved: Optional[bool] = Field(
        default=False,
        description="Whether an estimator has manually reviewed and approved this item",
        example=False,
    )


class ProposalOption(BaseModel):
    """Optional add-on proposal scope item, commercial charge, or service rate."""

    description: str = Field(..., description="Description of the proposal option or commercial item")
    quantity: Optional[float] = Field(None, description="Contractor stated quantity (e.g. 1.0)")
    unit: Optional[str] = Field(None, description="Unit of measure (e.g. LS, MO)")
    amount: Optional[float] = Field(None, description="Additional price or rate for this item")


class PaymentScheduleItem(BaseModel):
    """Proposal payment milestone and terms."""

    milestone: str = Field(..., description="Milestone or event for payment")
    amount: Optional[float] = Field(None, description="Payment amount due")


class ProposalTerms(BaseModel):
    """Proposal pricing, options, and payment schedule kept separate from takeoff scope quantities."""

    subtotal: Optional[float] = Field(None, description="Proposal subtotal before tax, only if stated")
    tax_rate: Optional[float] = Field(None, description="Explicitly stated sales tax rate as a percentage")
    tax_amount: Optional[float] = Field(None, description="Explicitly stated sales tax amount")
    base_proposal_total: Optional[float] = Field(None, description="Proposal grand total, preserving the source's stated total")
    options: List[ProposalOption] = Field(
        default_factory=list,
        description="Optional scope items with add-on pricing",
    )
    monitoring_rates: List[ProposalOption] = Field(
        default_factory=list,
        description="Monthly monitoring charges",
    )
    payment_schedule: List[PaymentScheduleItem] = Field(
        default_factory=list,
        description="Payment milestone schedule",
    )
    notes: List[str] = Field(
        default_factory=list,
        description="Proposal conditions, validity period, and notes",
    )
    customer_responsibilities: List[str] = Field(
        default_factory=list,
        description="Customer responsibilities and site requirements",
    )
    exclusions: List[str] = Field(
        default_factory=list,
        description="Explicit scope exclusions specified in the proposal",
    )
    installation_conditions: List[str] = Field(
        default_factory=list,
        description="Installation guide, working hours, and labor conditions",
    )
    contractor_responsibilities: List[str] = Field(
        default_factory=list,
        description="Contractor assumed delivery, assembly, and installation responsibilities",
    )
    warranties: List[str] = Field(
        default_factory=list,
        description="Workmanship guarantees, equipment warranty, and manufacturer terms",
    )
    general_conditions: List[str] = Field(
        default_factory=list,
        description="General contractual, insurance, title, and deviation conditions",
    )



class SectionSummary(BaseModel):
    """Aggregated summary of items within a takeoff section."""

    section_key: str = Field(..., description="Unique section key (e.g., 'base_sprinkler')")
    section_title: str = Field(..., description="Human-readable section title")
    item_count: int = Field(..., description="Total number of items in this section")
    items_with_quantity: int = Field(..., description="Count of items with an explicit stated quantity")
    items_without_quantity: int = Field(..., description="Count of scope items where quantity is null")
    items_needing_review: int = Field(..., description="Count of items flagged for review")
    items: List[TakeoffItem] = Field(..., description="List of takeoff items belonging to this section")


class TakeoffExtractionSummary(BaseModel):
    """High-level summary of the entire takeoff extraction."""

    total_items: int = Field(..., description="Total number of line items extracted across all sections")
    total_sections: int = Field(..., description="Number of active takeoff sections")
    total_items_with_quantity: int = Field(..., description="Total items having an explicit stated numerical quantity")
    total_items_missing_quantity: int = Field(..., description="Total items having quantity = null")
    total_review_required: int = Field(..., description="Total items flagged for estimator review")
    total_warnings: int = Field(..., description="Number of document-level warnings generated")


class TakeoffExtractionResponse(BaseModel):
    """Complete structured response for AI sprinkler bid takeoff extraction."""

    status: str = Field(..., example="success")
    filename: str = Field(..., example="contractor-proposal.pdf")
    total_pages_processed: int = Field(..., example=3)
    project_metadata: ProjectMetadata
    summary: TakeoffExtractionSummary
    sections: Dict[str, SectionSummary] = Field(
        ...,
        description="Categorized sections: base_sprinkler, temporary_standpipe, general_conditions, etc.",
    )
    all_items: List[TakeoffItem] = Field(..., description="Complete flattened list of all extracted takeoff items")
    warnings: List[str] = Field(
        default_factory=list,
        description="Document warnings for missing quantities, ambiguous units, duplicate lines, or vague scope",
    )
    proposal_terms: Optional[ProposalTerms] = Field(
        default=None,
        description="Proposal pricing, optional scope items, and payment schedule kept strictly separate from takeoff quantities",
    )
    raw_model_info: Dict[str, Any] = Field(
        default_factory=dict,
        description="Inference diagnostics: model name, latency in milliseconds, and token usage",
    )


class TakeoffReviewRequest(BaseModel):
    """Payload for editing and validating takeoff items in the review workflow."""

    project_metadata: ProjectMetadata = Field(..., description="Project metadata details")
    items: List[TakeoffItem] = Field(..., description="List of takeoff items being reviewed or edited")
    filename: Optional[str] = Field("takeoff.pdf", description="Original filename reference")
    total_pages_processed: Optional[int] = Field(1, description="Total pages processed")
    proposal_terms: Optional[ProposalTerms] = Field(None, description="Proposal pricing, options, and payment terms")


class TakeoffExportRequest(BaseModel):
    """Payload for generating downloadable Excel or CSV takeoff exports."""

    project_metadata: ProjectMetadata = Field(..., description="Project metadata header details")
    all_items: Optional[List[TakeoffItem]] = Field(None, description="Takeoff items to export")
    items: Optional[List[TakeoffItem]] = Field(None, description="Alternative field for takeoff items")
    sections: Optional[Dict[str, SectionSummary]] = Field(None, description="Optional pre-grouped section data")
    summary: Optional[TakeoffExtractionSummary] = Field(None, description="Optional summary metrics")
    proposal_terms: Optional[ProposalTerms] = Field(None, description="Separate proposal pricing and terms")
    filename: Optional[str] = Field("takeoff", description="Filename prefix for downloaded export")

