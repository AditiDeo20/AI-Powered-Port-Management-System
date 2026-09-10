"""Database-backed billing prediction service.

This module is deliberately independent from the RAG/LLM stack.  It reads the
authoritative billing records from PostgreSQL, evaluates the exported XGBoost
JSON artifact with a small pure-Python tree evaluator, and applies the tax
formula layer using rates from the database.  No database writes are made by
this service.
"""

from __future__ import annotations

import json
import csv
import math
import os
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Optional

import psycopg
from dotenv import load_dotenv

WORKFLOW_ROOT = Path(__file__).resolve().parent
load_dotenv(WORKFLOW_ROOT.parent / ".env")


DEFAULT_MODEL_PATH = WORKFLOW_ROOT / "models" / "billing_xgb_model.json"
DEFAULT_MANIFEST_PATH = WORKFLOW_ROOT / "models" / "billing_model_manifest.json"
DEFAULT_RULES_PATH = WORKFLOW_ROOT / "config" / "billing_rules.json"
DEFAULT_TAX_MAPPING_PATH = WORKFLOW_ROOT / "data" / "billing_tax_mapping.csv"


def _number(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        parsed = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _rate(value: Any) -> Optional[float]:
    parsed = _number(value)
    if parsed is None:
        return None
    return parsed / 100.0 if abs(parsed) >= 1 else parsed


def _period_index(year: int, month: int) -> int:
    return year * 12 + month


def _parse_period(value: Any) -> Optional[tuple[int, int]]:
    text = str(value or "").strip()
    if not re.fullmatch(r"20\d{4}", text):
        return None
    return int(text[:4]), int(text[4:])


def _month_after(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)


def _clean_customer(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    if not text:
        return None
    return text


@dataclass
class BillingPredictionRequest:
    customer_id: str = ""
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
    rates: dict[str, float] = field(default_factory=dict)
    allocated_rate_keys: list[str] = field(default_factory=list)


@dataclass
class BillingPredictionResult:
    context_id: str
    request: BillingPredictionRequest
    final_amount: float
    monthly_base_amount: float
    model_raw_output: float
    model_source: str
    model_path: str
    model_training_cutoff: Optional[str]
    model_metrics: dict[str, Any]
    formula_schedule: str
    tax_items: list[dict[str, Any]]
    total_formula_tax: float
    calculation_steps: list[str]
    data_source: str
    fallback_applied: bool
    fallback_reasons: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["request"] = asdict(self.request)
        return payload

    def summary(self) -> str:
        request = self.request
        display_bill_type = str(self.metadata.get("bill_type_label") or request.bill_type.replace("_", " "))
        lines = [
            f"Predicted {display_bill_type} for customer {request.customer_id or 'manual input'} "
            f"in {request.target_year}-{request.target_month:02d}: INR {self.final_amount:,.2f}",
            "",
            "Calculation breakdown:",
        ]
        lines.extend(f"{idx}. {step}" for idx, step in enumerate(self.calculation_steps, start=1))
        return "\n".join(lines)


class XgbJsonModel:
    """Evaluate the exported XGBoost JSON model without importing xgboost."""

    def __init__(self, model_path: Path, manifest_path: Path):
        self.model_path = model_path
        self.manifest_path = manifest_path
        self.model = json.loads(model_path.read_text(encoding="utf-8"))
        self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        learner = self.model["learner"]
        self.learner_model = learner["learner_model_param"]
        self.trees = learner["gradient_booster"]["model"]["trees"]
        self.feature_columns = list(self.manifest["feature_columns"])

    @property
    def metrics(self) -> dict[str, Any]:
        return dict(self.manifest.get("metrics") or {})

    def predict_log(self, values: dict[str, float]) -> float:
        base_score = str(self.learner_model.get("base_score", "0.0")).strip("[]")
        prediction = float(base_score.split(",")[0])
        vector = [float(values.get(column, 0.0)) for column in self.feature_columns]

        for tree in self.trees:
            node = 0
            left_children = tree["left_children"]
            right_children = tree["right_children"]
            while left_children[node] != -1:
                feature_index = tree["split_indices"][node]
                feature_value = vector[feature_index]
                if not math.isfinite(feature_value):
                    node = left_children[node] if tree["default_left"][node] else right_children[node]
                elif feature_value < tree["split_conditions"][node]:
                    node = left_children[node]
                else:
                    node = right_children[node]
            prediction += tree["base_weights"][node]
        return prediction


class BillingPredictionService:
    def __init__(self):
        self.rules_path = Path(os.getenv("BILLING_RULES_PATH", str(DEFAULT_RULES_PATH)))
        self.rules = self._read_rules(self.rules_path)
        configured_tax_mapping = os.getenv("BILLING_TAX_MAPPING_CSV", "").strip()
        self.tax_mapping_path = Path(configured_tax_mapping) if configured_tax_mapping else DEFAULT_TAX_MAPPING_PATH
        # This application uses DB_* settings; retain POSTGRES_* support for
        # compatibility with the source project.
        self.host = os.getenv("POSTGRES_HOST") or os.getenv("DB_HOST", "localhost")
        self.port = int(os.getenv("POSTGRES_PORT") or os.getenv("DB_PORT", "5432"))
        self.dbname = os.getenv("POSTGRES_DB") or os.getenv("DB_NAME", "postgres")
        self.user = os.getenv("POSTGRES_USER") or os.getenv("DB_USER", "postgres")
        self.password = os.getenv("POSTGRES_PASSWORD") or os.getenv("DB_PASSWORD", "")
        self.schema = os.getenv("POSTGRES_SCHEMA", "rag")
        self._tax_mapping_cache: Optional[tuple[int, dict[tuple[str, int], int], dict[str, list[list[str]]]]] = None
        configured_limit = os.getenv("BILLING_MAX_FORECAST_MONTHS")
        configured_rule_limit = self.rules.get("max_forecast_months")
        self.max_forecast_months = int(configured_limit) if configured_limit else (int(configured_rule_limit) if configured_rule_limit is not None else None)
        self.model_path = Path(os.getenv("BILLING_MODEL_PATH", str(DEFAULT_MODEL_PATH)))
        self.manifest_path = Path(os.getenv("BILLING_MODEL_MANIFEST_PATH", str(DEFAULT_MANIFEST_PATH)))
        self.model: Optional[XgbJsonModel] = None
        self.contexts: dict[str, BillingPredictionResult] = {}

        if not self.model_path.exists():
            raise FileNotFoundError(f"Billing model artifact not found: {self.model_path}")
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Billing model manifest not found: {self.manifest_path}")

    @staticmethod
    def _read_rules(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Billing rules file not found: {path}")
        rules = json.loads(path.read_text(encoding="utf-8"))
        required_sections = ("defaults", "months", "categories", "frequencies", "structures", "formula", "rates", "formula_schedules")
        missing = [section for section in required_sections if section not in rules]
        if missing:
            raise ValueError(f"Billing rules file is missing sections: {', '.join(missing)}.")
        return rules

    def rules_payload(self) -> dict[str, Any]:
        """Return only the configuration needed to render the billing form."""
        return {
            "version": self.rules.get("version"),
            "formula_source_file": self.rules.get("formula_source_file"),
            "defaults": self.rules["defaults"],
            "max_forecast_months": self.max_forecast_months,
            "months": self.rules["months"],
            "categories": [
                {key: category[key] for key in ("value", "label")}
                for category in self.rules["categories"]
            ],
            "frequencies": [
                {key: frequency[key] for key in ("value", "label")}
                for frequency in self.rules["frequencies"]
            ],
            "structures": [
                {key: structure[key] for key in ("value", "label", "factor")}
                for structure in self.rules["structures"]
            ],
            "rates": [
                {key: rate[key] for key in ("key", "label")}
                for rate in self.rules["rates"]
            ],
        }

    @staticmethod
    def _csv_column_index(headers: list[str], name: str, occurrence: int = 0) -> Optional[int]:
        matches = [index for index, header in enumerate(headers) if header == name]
        return matches[occurrence] if occurrence < len(matches) else None

    @staticmethod
    def _csv_value(row: list[str], columns: dict[tuple[str, int], int], name: str, occurrence: int = 0) -> str:
        index = columns.get((name, occurrence))
        return row[index].strip() if index is not None and index < len(row) else ""

    @staticmethod
    def _csv_bool(value: Any) -> Optional[bool]:
        text = str(value or "").strip().lower()
        if text in {"true", "t", "1", "yes", "y"}:
            return True
        if text in {"false", "f", "0", "no", "n"}:
            return False
        return None

    def _read_tax_mapping_csv(self) -> tuple[dict[tuple[str, int], int], dict[str, list[list[str]]]]:
        if self.tax_mapping_path is None or not self.tax_mapping_path.exists():
            raise FileNotFoundError("The configured billing tax-mapping CSV is not available.")
        modified_ns = self.tax_mapping_path.stat().st_mtime_ns
        if self._tax_mapping_cache and self._tax_mapping_cache[0] == modified_ns:
            return self._tax_mapping_cache[1], self._tax_mapping_cache[2]

        with self.tax_mapping_path.open(newline="", encoding="utf-8-sig") as source:
            reader = csv.reader(source)
            headers = next(reader, [])
            tenancy_index = self._csv_column_index(headers, "tenancy_id")
            if tenancy_index is None:
                raise ValueError("The tax-mapping CSV does not contain a tenancy_id column.")
            columns: dict[tuple[str, int], int] = {}
            seen: dict[str, int] = {}
            for index, name in enumerate(headers):
                occurrence = seen.get(name, 0)
                columns[(name, occurrence)] = index
                seen[name] = occurrence + 1
            grouped: dict[str, list[list[str]]] = {}
            for row in reader:
                tenancy_id = row[tenancy_index].strip() if len(row) > tenancy_index else ""
                if tenancy_id:
                    grouped.setdefault(tenancy_id, []).append(row)
        self._tax_mapping_cache = (modified_ns, columns, grouped)
        return columns, grouped

    def tenancy_options(self) -> list[dict[str, str]]:
        _, grouped = self._read_tax_mapping_csv()
        tenancy_ids = sorted(grouped)
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT DISTINCT trim(customercode), customerid::text
                        FROM public.mcustomer
                        WHERE trim(customercode) = ANY(%s)
                    """, (tenancy_ids,))
                    mappings = {str(code).strip(): str(customer_id) for code, customer_id in cur.fetchall()}
        except Exception:
            # The supplied CSV remains authoritative for tenancy choices when
            # a local PostgreSQL instance is not available.
            mappings = {}
        return [
            {"tenancy_id": tenancy_id, "customer_id": mappings.get(tenancy_id, "")}
            for tenancy_id in tenancy_ids
        ]

    def tenancy_prefill(self, tenancy_id: str) -> dict[str, Any]:
        """Return source-backed form values for one CSV tenancy mapping."""
        selected_tenancy = _clean_customer(tenancy_id)
        if not selected_tenancy:
            raise ValueError("tenancy_id is required.")
        columns, grouped = self._read_tax_mapping_csv()
        csv_rows = grouped.get(selected_tenancy, [])
        if not csv_rows:
            raise ValueError(f"No tax-mapping rows were found for tenancy {selected_tenancy}.")

        first_row = csv_rows[0]
        csv_frequency = self._normalize_frequency(self._csv_value(first_row, columns, "bill_periodicity", 1))
        csv_additional_rent = self._csv_bool(self._csv_value(first_row, columns, "has_additional_rent"))
        csv_structure_id = self._csv_value(first_row, columns, "Structure_type_id")

        with self._connect() as conn:
            customer_id = self._customer_id_for_tenancy(conn, selected_tenancy)
            profile = self._load_profile(conn, customer_id)
            additional_rent = csv_additional_rent
            if additional_rent is None:
                additional_rent = profile.get("is_additional_rent")
            bill_type = "additional_rent" if additional_rent else str(self.rules["defaults"]["category"])
            model_bill_type = self._model_bill_type(bill_type)
            history = self._load_history(conn, customer_id, model_bill_type)
            structure_source = self._load_tenancy_structure(conn, selected_tenancy, csv_structure_id)

        latest = history[-1] if history else None
        structure_input = self._configured_structure_value(
            structure_source.get("label"),
            profile.get("structure_type"),
            profile.get("main_structure_name"),
        )
        frequency = csv_frequency or profile.get("billing_frequency")
        rates, allocated_rate_keys, matched_tax_rows, rate_warnings = self._csv_formula_rates(csv_rows, columns)
        warnings = list(rate_warnings)
        if not history:
            warnings.append(f"No eligible {self._category_label(bill_type).lower()} history was found for customer {customer_id}.")
        if frequency is None:
            warnings.append("No billing frequency was available from the selected tenancy or customer profile.")
        if structure_input is None:
            raw_structure = structure_source.get("label") or profile.get("structure_type") or csv_structure_id
            if raw_structure:
                warnings.append(f"The source structure '{raw_structure}' has no matching formula structure rule.")
        if profile.get("area") is None:
            warnings.append("No property area was found in public.plot for the selected customer.")

        target_year = max(latest["period"][0] + 1, date.today().year + 1) if latest else None
        target_month = int(self.rules["defaults"]["target_month"]) if latest else None
        fields = {
            "present_year": latest["period"][0] if latest else None,
            "present_month": latest["period"][1] if latest else None,
            "target_year": target_year,
            "target_month": target_month,
            "present_amount": latest["amount"] if latest else None,
            "present_cgst": latest["cgst"] if latest else None,
            "present_sgst": latest["sgst"] if latest else None,
            "area": profile.get("area"),
            "billing_frequency": frequency,
            "bill_type": bill_type,
            "structure_type": structure_input,
        }
        return {
            "tenancy_id": selected_tenancy,
            "customer_id": customer_id,
            "fields": fields,
            "rates": rates,
            "allocated_rate_keys": allocated_rate_keys,
            "matched_tax_rows": matched_tax_rows,
            "warnings": warnings,
            "sources": {
                "customer_id": "public.mcustomer.customercode -> customerid",
                "present_bill": "public.tgeneralbill latest eligible bill for the CSV-derived bill type",
                "area": "public.plot.area matched by customer code or RR/plot number",
                "billing_frequency": "CSV applicant_property_mapping.bill_periodicity, then public.mcustomer.billperiodicity",
                "bill_type": "CSV applicant_property_mapping.has_additional_rent",
                "structure": "CSV applicant_property_mapping.Structure_type_id joined to public.m_structure_type",
                "formula_rates": "CSV tax rows with a configured exact tax-name match",
                "target_period": "Derived from the latest present bill period and configured default target month; not a historical source field",
            },
            "tax_allocation_basis": "CSV row presence for the selected tenancy; rows explicitly marked is_applicable=false or is_active=false are excluded. The export has no is_allocated column.",
        }

    def _customer_id_for_tenancy(self, conn, tenancy_id: str) -> str:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT mc.customerid::text
                FROM public.mcustomer mc
                WHERE trim(mc.customercode) = %s
                ORDER BY mc.customerid::text
            """, (tenancy_id,))
            customer_ids = [str(row[0]).strip() for row in cur.fetchall() if row[0] is not None]
        if not customer_ids:
            raise ValueError(f"No customer was found in public.mcustomer for tenancy {tenancy_id}.")
        if len(set(customer_ids)) > 1:
            raise ValueError(f"Tenancy {tenancy_id} maps to multiple customer IDs in public.mcustomer.")
        return customer_ids[0]

    def _configured_structure_value(self, *source_values: Any) -> Optional[str]:
        source_text = " ".join(self._normalise_match_text(value) for value in source_values if value)
        for structure in self.rules["structures"]:
            if self._normalise_match_text(structure.get("value")) in source_text:
                return str(structure["value"])
            if any(self._normalise_match_text(term) in source_text for term in structure.get("match_terms", [])):
                return str(structure["value"])
        return None

    @staticmethod
    def _normalise_match_text(value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "").strip().lower())

    def _csv_formula_rates(self, rows: list[list[str]], columns: dict[tuple[str, int], int]) -> tuple[dict[str, float], list[str], list[dict[str, Any]], list[str]]:
        selected: dict[str, tuple[date, Optional[float], dict[str, Any]]] = {}
        allocated_keys: set[str] = set()
        matched_tax_rows: list[dict[str, Any]] = []
        skipped_explicit = False
        for row in rows:
            if self._csv_bool(self._csv_value(row, columns, "is_active")) is False:
                continue
            if self._csv_bool(self._csv_value(row, columns, "is_applicable")) is False:
                skipped_explicit = True
                continue
            if self._csv_bool(self._csv_value(row, columns, "applicable_in_report")) is False:
                continue
            if self._csv_bool(self._csv_value(row, columns, "tax_in_percent")) is False:
                continue
            percent = _number(self._csv_value(row, columns, "tax_percent"))
            tax_name = self._csv_value(row, columns, "tax_name")
            tax_short = self._csv_value(row, columns, "tax_name_short")
            tax_code = self._csv_value(row, columns, "tax_code")
            valid_from_text = self._csv_value(row, columns, "valid_from")
            try:
                valid_from = date.fromisoformat(valid_from_text) if valid_from_text else date.min
            except ValueError:
                valid_from = date.min
            for definition in self.rules["rates"]:
                match = definition.get("csv_match") or {}
                names = {self._normalise_match_text(value) for value in match.get("tax_names", [])}
                shorts = {self._normalise_match_text(value) for value in match.get("tax_name_shorts", [])}
                codes = {self._normalise_match_text(value) for value in match.get("tax_codes", [])}
                if not (
                    self._normalise_match_text(tax_name) in names
                    or self._normalise_match_text(tax_short) in shorts
                    or self._normalise_match_text(tax_code) in codes
                ):
                    continue
                key = str(definition["key"])
                allocated_keys.add(key)
                item = {"tax_name": tax_name, "tax_code": tax_code, "tax_percent": percent, "valid_from": valid_from_text}
                current = selected.get(key)
                if current is None or valid_from >= current[0]:
                    selected[key] = (valid_from, percent, item)
        for key, (_, _, item) in selected.items():
            matched_tax_rows.append(item)
        matched_tax_rows.sort(key=lambda item: item["tax_name"])
        rates = {key: item[1] for key, item in selected.items() if item[1] is not None}
        warnings = ["The CSV export has no is_allocated column; formula-rate visibility uses selected-tenancy row presence and explicit opt-out fields."]
        if any(item[1] is None for item in selected.values()):
            warnings.append("At least one allocated formula tax has no percentage in the CSV, so its input was left blank.")
        if skipped_explicit:
            warnings.append("Some selected-tenancy tax rows were explicitly marked not applicable and were hidden.")
        return rates, sorted(allocated_keys), matched_tax_rows, warnings

    def _apply_request_defaults(self, request: BillingPredictionRequest) -> None:
        defaults = self.rules["defaults"]
        if not request.target_month:
            request.target_month = int(defaults["target_month"])
        if not request.bill_type:
            request.bill_type = str(defaults["category"])
        if request.water_tax_included is None:
            request.water_tax_included = bool(defaults["water_tax_included"])

    def _category_label(self, value: str) -> str:
        return next(
            (str(category["label"]) for category in self.rules["categories"]
             if value in {category["value"], category.get("model_value")}),
            value.replace("_", " "),
        )

    def _forecast_quality(self, model: XgbJsonModel, current_period: tuple[int, int], target_period: tuple[int, int]) -> dict[str, Any]:
        horizon = _period_index(*target_period) - _period_index(*current_period)
        cutoff = model.metrics.get("validation_cutoff")
        cutoff_match = re.fullmatch(r"(20\d{2})-(\d{2})", str(cutoff or ""))
        cutoff_period = (int(cutoff_match.group(1)), int(cutoff_match.group(2))) if cutoff_match else None
        beyond_cutoff = cutoff_period is not None and _period_index(*target_period) > _period_index(*cutoff_period)
        is_long_horizon = horizon > int(self.rules.get("long_horizon_threshold_months", 0))
        return {
            "status": "extrapolation" if beyond_cutoff or is_long_horizon else "within_validation_range",
            "forecast_horizon_months": horizon,
            "validation_cutoff": cutoff,
            "beyond_validation_cutoff": beyond_cutoff,
            "long_horizon": is_long_horizon,
        }

    @property
    def model_loaded(self) -> bool:
        return self.model is not None

    def _get_model(self) -> XgbJsonModel:
        if self.model is None:
            self.model = XgbJsonModel(self.model_path, self.manifest_path)
        return self.model

    def _connect(self):
        return psycopg.connect(
            host=self.host,
            port=self.port,
            dbname=self.dbname,
            user=self.user,
            password=self.password,
            connect_timeout=5,
        )

    def predict(self, request: BillingPredictionRequest) -> BillingPredictionResult:
        self._apply_request_defaults(request)
        self._validate(request)
        model = self._get_model()
        fallback_reasons: list[str] = []
        bill_type = self._model_bill_type(request.bill_type)

        with self._connect() as conn:
            history = self._load_history(conn, request.customer_id, bill_type)
            rates = self._load_rates(conn, request.target_year, request.target_month)
            profile = self._load_profile(conn, request.customer_id)

        if not history:
            raise ValueError(f"No eligible billing history was found for customer {request.customer_id}.")

        latest_period = history[-1]["period"]
        current_year = request.current_year or latest_period[0]
        current_month = request.current_month or latest_period[1]
        if _period_index(request.target_year, request.target_month) <= _period_index(current_year, current_month):
            raise ValueError("The target period must be after the latest available billing period.")
        self._validate_horizon(current_year, current_month, request.target_year, request.target_month)
        forecast_quality = self._forecast_quality(model, (current_year, current_month), (request.target_year, request.target_month))

        area = profile.get("area")
        if area is None:
            fallback_reasons.append("No reliable property area was found; model area features used zero.")
            area = 0.0
        frequency = profile.get("billing_frequency") or self._infer_frequency(history)
        if not profile.get("billing_frequency"):
            fallback_reasons.append("Billing periodicity was inferred from the customer's billing history.")

        current = history[-1]
        current_amount = current["amount"]
        current_cgst = current["cgst"]
        current_sgst = current["sgst"]
        target_period_index = _period_index(request.target_year, request.target_month)
        path: list[dict[str, Any]] = []
        current_period = (current_year, current_month)

        while _period_index(*current_period) < target_period_index:
            next_period = _month_after(*current_period)
            feature_values = self._feature_values(
                model=model,
                amount=current_amount,
                cgst=current_cgst,
                sgst=current_sgst,
                area=area,
                frequency=frequency,
                bill_type=bill_type,
                current_period=current_period,
                target_period=next_period,
            )
            raw = model.predict_log(feature_values)
            next_amount = max(0.0, math.expm1(raw))
            path.append({"year": next_period[0], "month": next_period[1], "raw": raw, "amount": next_amount})
            current_amount = next_amount
            current_cgst = next_amount * (current["cgst"] / current["amount"] if current["amount"] else 0.0)
            current_sgst = next_amount * (current["sgst"] / current["amount"] if current["amount"] else 0.0)
            current_period = next_period

        monthly_base = current_amount
        rates, rate_reasons = self._normalize_rates(rates)
        fallback_reasons.extend(rate_reasons)
        formula = self._apply_formula_layer(
            rules=self.rules,
            monthly_base=monthly_base,
            rates=rates,
            target_month=request.target_month,
            structure_type=request.structure_type or profile.get("structure_type"),
            water_tax_included=True if request.water_tax_included is None else request.water_tax_included,
            present_amount=current["amount"],
            present_cgst=current["cgst"],
            present_sgst=current["sgst"],
        )
        total = formula["final_amount"]
        result = BillingPredictionResult(
            context_id=str(uuid.uuid4()),
            request=request,
            final_amount=total,
            monthly_base_amount=monthly_base,
            model_raw_output=path[-1]["raw"] if path else math.log1p(monthly_base),
            model_source="xgboost-json",
            model_path=str(self.model_path),
            model_training_cutoff=(model.metrics.get("validation_cutoff") if model else None),
            model_metrics=model.metrics,
            formula_schedule=formula["formula_schedule"],
            tax_items=formula["tax_items"],
            total_formula_tax=formula["total_formula_tax"],
            calculation_steps=formula["calculation_steps"],
            data_source="postgres.public.tgeneralbill + master tables",
            fallback_applied=bool(fallback_reasons),
            fallback_reasons=fallback_reasons,
            metadata={
                "history_points": len(history),
                "latest_source_period": f"{latest_period[0]}-{latest_period[1]:02d}",
                "forecast_path": path,
                "billing_frequency": frequency,
                "profile": profile,
                "rates": rates,
                "bill_type_label": self._category_label(request.bill_type),
                "forecast_quality": forecast_quality,
                "formula_notice": formula.get("formula_notice", ""),
                "formula_source_file": formula.get("formula_source_file"),
            },
        )
        self.contexts[result.context_id] = result
        return result

    def predict_from_prompt(self, prompt: str) -> BillingPredictionResult:
        customer_match = re.search(r"\bcustomer(?:\s+id)?\s*(?:is|=|:)?\s*([A-Za-z0-9_-]+)", prompt or "", re.IGNORECASE)
        if not customer_match:
            raise ValueError("Please include a customer ID, for example: customer 1528.")
        year_match = re.search(r"\b(20\d{2})\b", prompt or "")
        target_year = int(year_match.group(1)) if year_match else date.today().year + 1
        target_month = int(self.rules["defaults"]["target_month"])
        lowered = (prompt or "").lower()
        month_names = {str(item["label"]).lower(): int(item["value"]) for item in self.rules["months"]}
        for name, month in month_names.items():
            if re.search(rf"\b{name}\b", lowered):
                target_month = month
                break
        if any(re.search(rf"\b{re.escape(term)}\b", lowered) for term in self.rules.get("excluded_prompt_terms", [])):
            raise ValueError(self.rules.get("excluded_prompt_message", ""))
        categories = self.rules["categories"]
        ordered_categories = sorted(
            categories,
            key=lambda category: max((len(str(alias)) for alias in category.get("prompt_aliases", [])), default=0),
            reverse=True,
        )
        bill_type = next(
            (category["value"] for category in ordered_categories
             if any(alias in lowered for alias in category.get("prompt_aliases", []))),
            self.rules["defaults"]["category"],
        )
        return self.predict(BillingPredictionRequest(
            customer_id=customer_match.group(1),
            target_year=target_year,
            target_month=target_month,
            bill_type=bill_type,
        ))

    def predict_from_inputs(self, request: BillingPredictionRequest) -> BillingPredictionResult:
        """Run the complete prediction-interface form without requiring a customer lookup."""
        self._apply_request_defaults(request)
        model = self._get_model()
        required = {
            "present_year": request.present_year,
            "present_month": request.present_month,
            "present_amount": request.present_amount,
            "present_cgst": request.present_cgst,
            "present_sgst": request.present_sgst,
            "area": request.area,
        }
        missing = [name for name, value in required.items() if value is None]
        if missing:
            raise ValueError(f"Complete the billing form. Missing: {', '.join(missing)}.")
        self._model_bill_type(request.bill_type)
        valid_months = {int(item["value"]) for item in self.rules["months"]}
        if int(request.present_month) not in valid_months or request.target_month not in valid_months:
            raise ValueError("Present and target months must be between 1 and 12.")
        if _period_index(request.target_year, request.target_month) <= _period_index(request.present_year, request.present_month):
            raise ValueError("Target month must be after the present bill month.")
        self._validate_horizon(request.present_year, request.present_month, request.target_year, request.target_month)
        forecast_quality = self._forecast_quality(model, (request.present_year, request.present_month), (request.target_year, request.target_month))

        amount = max(0.0, float(request.present_amount))
        cgst = max(0.0, float(request.present_cgst))
        sgst = max(0.0, float(request.present_sgst))
        area = max(0.0, float(request.area))
        frequency = self._normalize_frequency(request.billing_frequency) or self.rules["defaults"]["frequency"]
        current_period = (int(request.present_year), int(request.present_month))
        target_period = (request.target_year, request.target_month)
        cgst_rate = cgst / amount if amount else 0.0
        sgst_rate = sgst / amount if amount else 0.0
        path: list[dict[str, Any]] = []
        model_bill_type = self._model_bill_type(request.bill_type)
        while _period_index(*current_period) < _period_index(*target_period):
            next_period = _month_after(*current_period)
            values = self._feature_values(
                model=model, amount=amount, cgst=cgst, sgst=sgst, area=area,
                frequency=frequency, bill_type=model_bill_type,
                current_period=current_period, target_period=next_period,
            )
            raw = model.predict_log(values)
            amount = max(0.0, math.expm1(raw))
            cgst = amount * cgst_rate
            sgst = amount * sgst_rate
            path.append({"year": next_period[0], "month": next_period[1], "raw": raw, "amount": amount})
            current_period = next_period

        raw_rates = dict(request.rates or {})
        allocated_rate_keys = set(request.allocated_rate_keys or raw_rates.keys())
        database_rates: dict[str, Any] = {}
        rate_reasons: list[str] = []
        try:
            with self._connect() as conn:
                database_rates = self._load_rates(conn, request.target_year, request.target_month)
        except Exception as error:
            rate_reasons.append(f"Database tax rates were unavailable ({type(error).__name__}); only selected source rates were used.")
        for key in allocated_rate_keys:
            if raw_rates.get(key) in (None, "") and key in database_rates:
                raw_rates[key] = database_rates[key]
        rates, normalization_reasons = self._normalize_rates(raw_rates)
        rate_reasons.extend(normalization_reasons)
        formula = self._apply_formula_layer(
            rules=self.rules,
            monthly_base=amount,
            rates=rates,
            target_month=request.target_month,
            structure_type=request.structure_type,
            water_tax_included=True if request.water_tax_included is None else request.water_tax_included,
            present_amount=float(request.present_amount or 0),
            present_cgst=float(request.present_cgst or 0),
            present_sgst=float(request.present_sgst or 0),
        )
        result = BillingPredictionResult(
            context_id=str(uuid.uuid4()),
            request=request,
            final_amount=formula["final_amount"],
            monthly_base_amount=amount,
            model_raw_output=path[-1]["raw"] if path else math.log1p(amount),
            model_source="xgboost-json",
            model_path=str(self.model_path),
            model_training_cutoff=model.metrics.get("validation_cutoff"),
            model_metrics=model.metrics,
            formula_schedule=formula["formula_schedule"],
            tax_items=formula["tax_items"],
            total_formula_tax=formula["total_formula_tax"],
            calculation_steps=formula["calculation_steps"],
            data_source="complete billing form + exported XGBoost model artifact",
            fallback_applied=bool(rate_reasons),
            fallback_reasons=rate_reasons,
            metadata={"history_points": 1, "forecast_path": path, "billing_frequency": frequency, "rates": rates, "database_rates": database_rates, "allocated_rate_keys": sorted(allocated_rate_keys), "manual_inputs": True, "bill_type_label": self._category_label(request.bill_type), "forecast_quality": forecast_quality, "formula_notice": formula.get("formula_notice", ""), "formula_source_file": formula.get("formula_source_file")},
        )
        self.contexts[result.context_id] = result
        return result

    def follow_up(self, context_id: str, prompt: str) -> BillingPredictionResult:
        previous = self.contexts.get(context_id)
        if previous is None:
            raise ValueError("The billing prediction context has expired. Please run a new forecast.")
        year_match = re.search(r"\b(20\d{2})\b", prompt or "")
        month = previous.request.target_month
        lowered = (prompt or "").lower()
        month_names = {str(item["label"]).lower(): int(item["value"]) for item in self.rules["months"]}
        for name, month_value in month_names.items():
            if re.search(rf"\b{name}\b", lowered):
                month = month_value
                break
        request = BillingPredictionRequest(
            customer_id=previous.request.customer_id,
            target_year=int(year_match.group(1)) if year_match else previous.request.target_year,
            target_month=month,
            bill_type=previous.request.bill_type,
            current_year=previous.request.current_year,
            current_month=previous.request.current_month,
            structure_type=previous.request.structure_type,
            water_tax_included=previous.request.water_tax_included,
        )
        return self.predict(request)

    def _load_history(self, conn, customer_id: str, bill_type: str) -> list[dict[str, Any]]:
        category = next(
            (item for item in self.rules["categories"] if item.get("model_value") == bill_type),
            None,
        )
        if category is None:
            raise ValueError(f"No billing rule is configured for model category '{bill_type}'.")
        charge_ids = category["charge_ids"]
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    trim(tg.billyearmonth::text) AS bill_period,
                    SUM(COALESCE(tg.amount, 0))::double precision AS amount,
                    SUM(COALESCE(tg.cgst, 0))::double precision AS cgst,
                    SUM(COALESCE(tg.sgst, 0))::double precision AS sgst
                FROM public.tgeneralbill tg
                WHERE trim(tg.customerid) = %s
                  AND tg.billchargeid = ANY(%s)
                  AND trim(tg.billyearmonth::text) ~ '^20[0-9]{4}$'
                  AND COALESCE(tg.amount, 0) > 0
                GROUP BY trim(tg.billyearmonth::text)
                ORDER BY trim(tg.billyearmonth::text)
            """, (str(customer_id), charge_ids))
            rows = cur.fetchall()
        history: list[dict[str, Any]] = []
        for period_text, amount, cgst, sgst in rows:
            parsed = _parse_period(period_text)
            if not parsed:
                continue
            history.append({"period": parsed, "amount": float(amount or 0), "cgst": float(cgst or 0), "sgst": float(sgst or 0)})
        return history

    def _load_profile(self, conn, customer_id: str) -> dict[str, Any]:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    mc.billperiodicity,
                    mc.rrplotno,
                    mc.customercode,
                    mc.typeofconstructionid,
                    mc.isadditionalrent,
                    p.area,
                    p.main_structure_name
                FROM public.mcustomer mc
                LEFT JOIN LATERAL (
                    SELECT area, main_structure_name
                    FROM public.plot
                    WHERE plot.customer_code = mc.customercode
                       OR plot.rr_no = mc.rrplotno
                    ORDER BY is_active DESC NULLS LAST, plot_id DESC
                    LIMIT 1
                ) p ON TRUE
                WHERE mc.customerid = %s
                ORDER BY mc.modifieddate DESC NULLS LAST
                LIMIT 1
            """, (int(customer_id) if str(customer_id).isdigit() else -1,))
            row = cur.fetchone()
        if not row:
            return {}
        billing_frequency = self._normalize_frequency(row[0])
        return {
            "billing_frequency": billing_frequency,
            "rrplotno": row[1],
            "customercode": row[2],
            "structure_type": row[3],
            "main_structure_name": row[6],
            "is_additional_rent": self._csv_bool(row[4]),
            "area": _number(row[5]),
        }

    def _load_tenancy_structure(self, conn, tenancy_id: str, csv_structure_id: str = "") -> dict[str, Any]:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT trim(apm."Structure_type_id"), st.structure_type
                FROM public.applicant_property_mapping apm
                LEFT JOIN public.m_structure_type st
                  ON st.structure_type_id = CASE
                       WHEN trim(apm."Structure_type_id") ~ '^[0-9]+$'
                       THEN trim(apm."Structure_type_id")::integer
                     END
                WHERE trim(apm.tenancy_id) = %s
                ORDER BY apm.update_timestamp DESC NULLS LAST
                LIMIT 1
            """, (tenancy_id,))
            row = cur.fetchone()
        if not row:
            return {"id": csv_structure_id or None, "label": None}
        return {"id": row[0] or csv_structure_id or None, "label": row[1] or None}

    def _load_rates(self, conn, year: int, month: int) -> dict[str, Any]:
        target = date(year, month, 1)
        database_rates = [rate for rate in self.rules["rates"] if rate.get("database_column")]
        columns = [str(rate["database_column"]) for rate in database_rates]
        if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", column) for column in columns):
            raise ValueError("Billing rules contain an invalid database column name.")
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT {', '.join(columns)}
                FROM public.m_tax_rates
                WHERE tax_period_from <= %s
                  AND (tax_period_to IS NULL OR tax_period_to >= %s)
                ORDER BY tax_period_from DESC
                LIMIT 1
            """, (target, target))
            row = cur.fetchone()
            cur.execute("""
                SELECT lower(tax_name), tax_percentage
                FROM public.m_tax_for_treecess_street_edu
                WHERE period_from <= %s
                  AND (period_to IS NULL OR period_to >= %s)
                ORDER BY period_from DESC
            """, (target, target))
            schedule_rows = cur.fetchall()
        rates: dict[str, Any] = {}
        if row:
            rates.update({rate["key"]: row[index] for index, rate in enumerate(database_rates)})
        for name, value in schedule_rows:
            for rate in self.rules["rates"]:
                term = rate.get("schedule_term")
                if term and term in name:
                    rates[rate["key"]] = value
        return rates

    def _normalize_rates(self, raw: dict[str, Any]) -> tuple[dict[str, float], list[str]]:
        rates: dict[str, float] = {}
        reasons: list[str] = []
        for rate_definition in self.rules["rates"]:
            name = rate_definition["key"]
            parsed = _rate(raw.get(name))
            if parsed is None:
                reasons.append(f"No database rate was found for {name}; that tax component was treated as zero.")
                parsed = 0.0
            rates[name] = parsed
        return rates, reasons

    def _normalize_frequency(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        for frequency in self.rules["frequencies"]:
            aliases = [str(alias).lower().replace("-", "_").replace(" ", "_") for alias in frequency.get("aliases", [])]
            if text == frequency["value"] or text in aliases:
                return frequency["value"]
        return None

    def _model_bill_type(self, value: str) -> str:
        for category in self.rules["categories"]:
            if value in {category["value"], category.get("model_value")}:
                return str(category["model_value"])
        labels = ", ".join(str(category["label"]) for category in self.rules["categories"])
        raise ValueError(f"The billing model supports only: {labels}.")

    def _validate_horizon(self, current_year: int, current_month: int, target_year: int, target_month: int) -> None:
        horizon = _period_index(target_year, target_month) - _period_index(current_year, current_month)
        if self.max_forecast_months is not None and horizon > self.max_forecast_months:
            raise ValueError(f"The target is {horizon} months away. The billing model is limited to {self.max_forecast_months} forecast months; choose a nearer target period.")

    def _infer_frequency(self, history: list[dict[str, Any]]) -> str:
        if len(history) < 2:
            return str(self.rules["defaults"]["frequency"])
        gaps = [
            _period_index(*history[idx]["period"]) - _period_index(*history[idx - 1]["period"])
            for idx in range(1, len(history))
        ]
        median = sorted(gaps)[len(gaps) // 2]
        ordered = sorted(self.rules["frequencies"], key=lambda item: int(item.get("minimum_gap", 0)), reverse=True)
        return next((item["value"] for item in ordered if median >= int(item.get("minimum_gap", 0))), self.rules["defaults"]["frequency"])

    @staticmethod
    def _feature_values(*, model: XgbJsonModel, amount: float, cgst: float, sgst: float, area: float,
                        frequency: str, bill_type: str, current_period: tuple[int, int], target_period: tuple[int, int]) -> dict[str, float]:
        values = {
            "present_amount": amount,
            "present_cgst": cgst,
            "present_sgst": sgst,
            "present_area": max(0.0, area),
            "present_year": float(current_period[0]),
            "present_month": float(current_period[1]),
            "target_year": float(target_period[0]),
            "target_month": float(target_period[1]),
            "horizon_months": float(_period_index(*target_period) - _period_index(*current_period)),
            "present_amount_per_area": amount / area if area > 0 else 0.0,
            "present_log_amount": math.log1p(max(0.0, amount)),
            "billing_frequency_monthly": 1.0 if frequency == "monthly" else 0.0,
            "billing_frequency_yearly": 1.0 if frequency == "yearly" else 0.0,
            "line_category_additional_rent": 1.0 if bill_type == "additional_rent" else 0.0,
            "line_category_rent": 1.0 if bill_type == "rent" else 0.0,
        }
        return {column: values.get(column, 0.0) for column in model.feature_columns}

    @staticmethod
    def _apply_formula_layer(*, rules: dict[str, Any], monthly_base: float, rates: dict[str, float], target_month: int,
                             structure_type: Optional[str], water_tax_included: bool,
                             present_amount: float = 0.0,
                             present_cgst: float = 0.0, present_sgst: float = 0.0) -> dict[str, Any]:
        structure_text = str(structure_type or "").lower()
        structure = next((item for item in rules["structures"] if item["value"] == structure_type), None)
        if structure is None:
            structure = next((item for item in rules["structures"] if any(term in structure_text for term in item.get("match_terms", []))), None)
        if structure is None:
            structure = next(item for item in rules["structures"] if item["value"] == rules["defaults"]["structure"])
        factor = float(structure["factor"])
        formula_rules = rules["formula"]
        months_per_year = float(formula_rules["months_per_year"])
        letting_value_divisor = float(formula_rules["letting_value_divisor"])
        deduction_rate = float(formula_rules["deduction_rate"])
        nrv_divisor = float(formula_rules["nrv_divisor"])
        half_year_divisor = float(formula_rules["half_year_divisor"])
        tax_split_divisor = float(formula_rules["tax_split_divisor"])
        annual_amount = monthly_base * months_per_year
        letting_value = annual_amount + annual_amount / letting_value_divisor
        grvp = letting_value - ((letting_value * deduction_rate) * deduction_rate)
        nrvp = grvp - grvp / nrv_divisor
        grvs = grvp - annual_amount
        nrvs = grvs - grvs / nrv_divisor
        half_annual = annual_amount / half_year_divisor

        def dual(rate: float) -> float:
            return (half_annual * factor * rate) + (nrvs / tax_split_divisor * rate)

        tax_items: list[dict[str, Any]] = []
        tax_calculation_steps: list[str] = []
        formula_notice = ""
        if target_month in {item for schedule_item in rules["formula_schedules"] for item in schedule_item.get("months", [])}:
            selected_schedule = next(item for item in rules["formula_schedules"] if target_month in item.get("months", []))
            schedule = selected_schedule["label"]
            for item in selected_schedule.get("items", []):
                kind = item.get("kind")
                if kind == "property_tax":
                    property_keys = item.get("rate_keys", [])
                    property_tax_enabled = structure["value"] == formula_rules.get("property_tax_structure", "mbpt")
                    general_value = (nrvs * rates.get(property_keys[0], 0.0) / tax_split_divisor) if property_keys and property_tax_enabled else 0.0
                    sewerage_value = (nrvp * rates.get(property_keys[1], 0.0) / tax_split_divisor) if len(property_keys) > 1 and property_tax_enabled else 0.0
                    water_value = (nrvp * rates.get(property_keys[2], 0.0) / tax_split_divisor) if len(property_keys) > 2 and water_tax_included and property_tax_enabled else 0.0
                    value = general_value + sewerage_value + water_value
                    tax_items.append({
                        "label": item["label"],
                        "formula": "(NRVS × General)/2 + (NRVP × Sewerage)/2 + (NRVP × Water)/2",
                        "components": {"general": general_value, "sewerage": sewerage_value, "water": water_value},
                        "value": value,
                    })
                    if property_tax_enabled:
                        property_parts = [
                            f"({nrvs:,.2f} × {rates.get(property_keys[0], 0.0):.2%})/2",
                            f"({nrvp:,.2f} × {rates.get(property_keys[1], 0.0):.2%})/2",
                        ]
                        if len(property_keys) > 2 and water_tax_included:
                            property_parts.append(f"({nrvp:,.2f} × {rates.get(property_keys[2], 0.0):.2%})/2")
                        tax_calculation_steps.append(f"{item['label']}: {' + '.join(property_parts)} = INR {value:,.2f}.")
                    else:
                        tax_calculation_steps.append(
                            f"{item['label']}: INR 0.00 because the source formula applies property tax only to the configured MbPT structure."
                        )
                elif kind == "dual":
                    rate_key = item.get("rate_key")
                    rate = rates.get(rate_key, 0.0)
                    part_a = half_annual * factor * rate
                    part_b = nrvs / tax_split_divisor * rate
                    value = part_a + part_b
                    tax_items.append({
                        "label": item["label"],
                        "formula": "((AM/2) × Const × rate) + ((NRVS/2) × rate)",
                        "components": {"annual_amount_part": part_a, "structure_part": part_b},
                        "value": value,
                    })
                    tax_calculation_steps.append(
                        f"{item['label']}: (({annual_amount:,.2f}/2) × {factor:.3f} × {rate:.2%}) + "
                        f"(({nrvs:,.2f}/2) × {rate:.2%}) = INR {value:,.2f}."
                    )
                elif kind == "street":
                    rate_key = item.get("rate_key")
                    rate = rates.get(rate_key, 0.0)
                    value = nrvp * rate / tax_split_divisor
                    tax_items.append({
                        "label": item["label"],
                        "formula": "(NRVP × Street rate) / 2",
                        "components": {"property_part": value},
                        "value": value,
                    })
                    tax_calculation_steps.append(
                        f"{item['label']}: ({nrvp:,.2f} × {rate:.2%})/2 = INR {value:,.2f}."
                    )
                else:
                    continue
        else:
            schedule = rules.get("unscheduled_formula_label", "")
            formula_notice = (
                f"No formula tax is billed in target month {target_month}; the source schedule bills pre taxes in April/October "
                "and post taxes in March/September."
            )
            tax_calculation_steps.append(formula_notice)

        taxable_base = monthly_base
        cgst_rate = max(0.0, present_cgst / present_amount) if present_amount > 0 else 0.0
        sgst_rate = max(0.0, present_sgst / present_amount) if present_amount > 0 else 0.0
        predicted_cgst = taxable_base * cgst_rate
        predicted_sgst = taxable_base * sgst_rate
        total_tax = sum(item["value"] for item in tax_items)
        final_amount = taxable_base + predicted_cgst + predicted_sgst + total_tax
        steps = [
            f"Forecast base amount = INR {monthly_base:,.2f}.",
            f"Predicted CGST = INR {predicted_cgst:,.2f}; predicted SGST = INR {predicted_sgst:,.2f} using the present bill rates.",
            f"Annual amount (AM) = INR {annual_amount:,.2f}.",
            f"Letting value (LV) = INR {letting_value:,.2f}.",
            f"Net rateable value property (NRVP) = INR {nrvp:,.2f}.",
            f"Net rateable value structure (NRVS) = INR {nrvs:,.2f}.",
            f"Formula schedule = {schedule}; NRV factor = {factor:.3f}.",
            *tax_calculation_steps,
            f"Formula taxes = INR {total_tax:,.2f}; final predicted amount = INR {final_amount:,.2f}.",
        ]
        return {
            "final_amount": final_amount,
            "formula_schedule": schedule,
            "formula_notice": formula_notice,
            "tax_items": tax_items,
            "total_formula_tax": total_tax,
            "calculation_steps": steps,
            "formula_source_file": rules.get("formula_source_file"),
        }

    def _validate(self, request: BillingPredictionRequest) -> None:
        if not _clean_customer(request.customer_id):
            raise ValueError("customer_id is required.")
        valid_months = {int(item["value"]) for item in self.rules["months"]}
        if request.target_month not in valid_months:
            raise ValueError("target_month must be between 1 and 12.")
        if request.target_year < 2000:
            raise ValueError("target_year must be a valid four-digit year.")
