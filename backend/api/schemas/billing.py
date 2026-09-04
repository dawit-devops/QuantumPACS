"""Pydantic v2 request schemas for the R09 Cashier/Billing module.

All money fields are floats in the API contract; the database stores
NUMERIC(12,2) and every response converts Decimals with db.billing.money().
"""
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class PricingItemRequest(BaseModel):
    procedure_code: str = Field(description="Procedure code (unique catalog key)")
    description: str = Field('', description="Human-readable procedure description")
    list_price: float = Field(..., gt=0, description="List price (must be positive)")
    active: bool = Field(True, description="Whether the item is active for invoicing")


class InvoiceLineRequest(BaseModel):
    procedure_code: str = Field('', description="Catalog procedure code (priced from catalog when given)")
    description: str = Field('', description="Free-text line description")
    quantity: int = Field(1, description="Quantity of the line item")
    unit_price: float = Field(0, description="Unit price fallback when procedure_code is absent/unknown")
    discount_amount: float = Field(0, description="Discount applied to the line")


class CreateInvoiceRequest(BaseModel):
    patient_id: str = Field(description="Primary patient identifier (MRN)")
    lines: list[InvoiceLineRequest] = Field(description="Invoice line items", min_length=1)


class PaymentRequest(BaseModel):
    method: Literal['cash', 'card', 'check'] = Field(description="Payment method")
    amount: float = Field(..., gt=0, description="Payment amount (must be positive)")
    idempotency_key: str = Field(..., min_length=1, description="Client-supplied key for duplicate payment detection")
    processor_token: str = Field('', description="Card processor token — never a raw PAN")
    split_group_id: str = Field('', description="Optional grouping key for split payments")


class CreateClaimRequest(BaseModel):
    status: Literal['submitted', 'acknowledged', 'denied', 'appeal'] = Field(
        'submitted', description="Claim status on creation",
    )
    source: Literal['external_feed', 'manual'] = Field('manual', description="Claim origin")
    external_claim_id: str = Field('', description="Reference from an external claims feed")


class UpdateClaimRequest(BaseModel):
    status: Literal['submitted', 'acknowledged', 'denied', 'appeal'] | None = Field(
        None, description="Updated claim status",
    )
    action_required: bool | None = Field(None, description="Whether follow-up action is required")
    external_claim_id: str | None = Field(None, description="Updated external claim reference")


class CreateRefundRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Refund amount (must be positive)")
    reason: str = Field(..., min_length=1, description="Reason for the refund")
    payment_id: str | None = Field(None, description="Optional originating payment")


class RefundActionRequest(BaseModel):
    action: Literal['approve', 'reject'] = Field(description="Refund decision")


class CreateQuoteRequest(BaseModel):
    patient_id: str = Field(description="Primary patient identifier (MRN)")
    procedure_code: str = Field(description="Catalog procedure code being quoted")
    invoice_id: str | None = Field(None, description="Optional invoice this quote relates to")
    estimated_patient_responsibility: float | None = Field(
        None, description="Estimated patient amount (defaults to catalog total)",
    )


class InstallmentRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Installment amount (must be positive)")
    due_date: date = Field(description="Installment due date")


class CreatePaymentPlanRequest(BaseModel):
    installments: list[InstallmentRequest] = Field(description="Payment plan installments", min_length=1)


class ReconciliationCloseRequest(BaseModel):
    shift_date: date = Field(description="Shift date being reconciled")
    counted_cash: dict[str, float] = Field(
        description="Counted totals per method with keys cash/card/check",
    )
    variance_reason: str = Field('', description="Required when counted totals differ from expected")


# ---------------------------------------------------------------------------
# B-09 Fee Schedule — edit, import, version history
# ---------------------------------------------------------------------------

class FeeScheduleUpdateRequest(BaseModel):
    list_price: float | None = Field(None, gt=0, description="New list price")
    description: str | None = Field(None, max_length=200)


class FeeScheduleImportRow(BaseModel):
    procedure_code: str = Field(..., min_length=1, max_length=40)
    description: str = Field('', max_length=200)
    list_price: float = Field(..., ge=0)


class FeeScheduleImportRequest(BaseModel):
    rows: list[FeeScheduleImportRow] = Field(..., min_length=1, max_length=5000)


# ---------------------------------------------------------------------------
# B-08 Payer Contract Rates
# ---------------------------------------------------------------------------

class CreatePayerContractRequest(BaseModel):
    payer_id: str = Field(..., min_length=1, max_length=80)
    payer_name: str = Field('', max_length=200)
    procedure_code: str = Field(..., min_length=1, max_length=40)
    contracted_rate: float = Field(..., ge=0)
    effective_date: str | None = Field(None, description="YYYY-MM-DD")


class UpdatePayerContractRequest(BaseModel):
    contracted_rate: float | None = Field(None, ge=0)
    effective_date: str | None = Field(None, description="YYYY-MM-DD")
    active: bool | None = Field(None)
