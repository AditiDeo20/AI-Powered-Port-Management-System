"""Billing forecasting and tender-publication workflow API.

The implementation and reference data are imported from the supplied
``prediction-part-integrated`` project and are kept separate from the core
lease-management routes.
"""

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from workflows.billing_prediction_service import BillingPredictionRequest, BillingPredictionService
from workflows.tender_workflow_service import TenderWorkflowError, TenderWorkflowService


workflow_router = APIRouter(prefix="/api", tags=["Billing forecast and tender workflow"])


class BillingRequest(BaseModel):
    customer_id: Optional[str] = None
    tenancy_id: Optional[str] = None
    target_year: int = 0
    target_month: int = 0
    bill_type: str = ""
    current_year: Optional[int] = None
    current_month: Optional[int] = None
    structure_type: Optional[str] = None
    water_tax_included: Optional[bool] = None
    present_year: Optional[int] = None
    present_month: Optional[int] = None
    present_amount: Optional[float] = None
    present_cgst: Optional[float] = None
    present_sgst: Optional[float] = None
    billing_frequency: Optional[str] = None
    area: Optional[float] = None
    line_category: Optional[str] = None
    rates: dict[str, float] = Field(default_factory=dict)
    allocated_rate_keys: list[str] = Field(default_factory=list)


class TenderWorkflowCreateRequest(BaseModel):
    plot_id: str
    checklist_key: str
    fields: dict[str, Any] = Field(default_factory=dict)
    checklist_answers: dict[str, str] = Field(default_factory=dict)


class TenderWorkflowActionRequest(BaseModel):
    action: str
    fields: dict[str, Any] = Field(default_factory=dict)
    checklist_answers: dict[str, str] = Field(default_factory=dict)
    comment: str = ""


class TenderCalculationRequest(BaseModel):
    fields: dict[str, Any] = Field(default_factory=dict)


try:
    billing_predictor: Optional[BillingPredictionService] = BillingPredictionService()
    billing_error: Optional[str] = None
except Exception as exc:  # The tender workflow remains available if billing setup fails.
    billing_predictor = None
    billing_error = str(exc)

tender_workflow = TenderWorkflowService()


def _billing_service() -> BillingPredictionService:
    if billing_predictor is None:
        raise HTTPException(status_code=503, detail=billing_error or "Billing forecast is unavailable.")
    return billing_predictor


@workflow_router.get("/workflow/health")
def workflow_health() -> dict[str, Any]:
    return {"status": "online", "billing_ready": billing_predictor is not None, "billing_error": billing_error}


@workflow_router.get("/health")
def workflow_tool_health() -> dict[str, Any]:
    """Compatibility response for the imported workflow interface."""
    return {"status": "online", "rag_services_ready": True, "billing_ready": billing_predictor is not None, "init_error": billing_error}


@workflow_router.get("/billing/status")
def billing_status() -> dict[str, Any]:
    service = _billing_service()
    return {"ready": True, "model": str(service.model_path)}


@workflow_router.get("/billing/rules")
def billing_rules() -> dict[str, Any]:
    return _billing_service().rules_payload()


@workflow_router.get("/billing/tenancies")
def billing_tenancies() -> dict[str, Any]:
    try:
        return {"options": _billing_service().tenancy_options()}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@workflow_router.get("/billing/tenancies/{tenancy_id}/prefill")
def billing_tenancy_prefill(tenancy_id: str) -> dict[str, Any]:
    try:
        return _billing_service().tenancy_prefill(tenancy_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@workflow_router.post("/billing/predict")
def billing_predict(request: BillingRequest) -> dict[str, Any]:
    try:
        payload = request.model_dump(exclude_none=True)
        forecast_request = BillingPredictionRequest(**payload)
        service = _billing_service()
        result = service.predict_from_inputs(forecast_request) if forecast_request.present_amount is not None else service.predict(forecast_request)
        return {"success": True, "summary": result.summary(), "prediction": result.as_dict()}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@workflow_router.get("/tender/config")
def tender_config() -> dict[str, Any]:
    try:
        return tender_workflow.config_payload()
    except TenderWorkflowError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@workflow_router.get("/tender/plots")
def tender_plots() -> dict[str, Any]:
    return {"plots": tender_workflow.list_plots()}


@workflow_router.get("/tender/plots/{plot_id}")
def tender_plot_detail(plot_id: str) -> dict[str, Any]:
    try:
        return tender_workflow.plot_detail(plot_id)
    except TenderWorkflowError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@workflow_router.get("/tender/checklists/{checklist_key}")
def tender_checklist(checklist_key: str) -> dict[str, Any]:
    try:
        return tender_workflow.checklist(checklist_key)
    except TenderWorkflowError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@workflow_router.post("/tender/calculate")
def tender_calculate(request: TenderCalculationRequest) -> dict[str, Any]:
    try:
        return tender_workflow.calculate(request.fields)
    except TenderWorkflowError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@workflow_router.get("/tender/workflows")
def tender_workflows() -> dict[str, Any]:
    return {"workflows": tender_workflow.list_workflows()}


@workflow_router.post("/tender/workflows")
def tender_create_workflow(request: TenderWorkflowCreateRequest) -> dict[str, Any]:
    try:
        return tender_workflow.create_workflow(request.model_dump())
    except TenderWorkflowError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@workflow_router.get("/tender/workflows/{workflow_id}")
def tender_get_workflow(workflow_id: str) -> dict[str, Any]:
    try:
        return tender_workflow.get_workflow(workflow_id)
    except TenderWorkflowError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@workflow_router.post("/tender/workflows/{workflow_id}/actions")
def tender_apply_action(workflow_id: str, request: TenderWorkflowActionRequest) -> dict[str, Any]:
    try:
        return tender_workflow.apply_action(workflow_id, request.model_dump())
    except TenderWorkflowError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@workflow_router.get("/tender/workflows/{workflow_id}/documents/{document_kind}")
def tender_document(workflow_id: str, document_kind: str):
    from fastapi.responses import Response

    try:
        content = tender_workflow.document_pdf(workflow_id, document_kind)
        return Response(content=content, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{document_kind}-{workflow_id}.pdf"'})
    except TenderWorkflowError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
