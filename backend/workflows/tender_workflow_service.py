"""Source-backed Tender Publication workflow service.

This module deliberately keeps commercial and approval values as workflow inputs.
The data exports contain plot context, but they do not provide a complete approved
rate/policy schedule for a publishable tender.
"""

from __future__ import annotations

import csv
import json
import math
import re
import threading
import uuid
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class TenderWorkflowError(ValueError):
    """Raised for invalid workflow requests that the API can return to the UI."""


class TenderWorkflowService:
    def __init__(self) -> None:
        # This service lives directly under backend/workflows in the integrated app.
        self.project_root = Path(__file__).resolve().parent
        self.data_dir = self.project_root / "data"
        self.data2_dir = self.project_root / "data2"
        self.config_path = self.project_root / "config" / "tender_workflow.json"
        self.storage_path = self.data_dir / "tender_workflows.json"
        self._lock = threading.RLock()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _normalise(value: Any) -> str:
        return str(value or "").strip().casefold()

    @staticmethod
    def _clean_number(value: Any, field_name: str, *, positive: bool = False) -> float:
        if value is None or str(value).strip() == "":
            raise TenderWorkflowError(f"{field_name} is required.")
        try:
            number = float(str(value).replace(",", "").strip())
        except (TypeError, ValueError) as error:
            raise TenderWorkflowError(f"{field_name} must be a valid number.") from error
        if not math.isfinite(number):
            raise TenderWorkflowError(f"{field_name} must be finite.")
        if positive and number <= 0:
            raise TenderWorkflowError(f"{field_name} must be greater than zero.")
        if not positive and number < 0:
            raise TenderWorkflowError(f"{field_name} cannot be negative.")
        return number

    def _config(self) -> dict[str, Any]:
        try:
            return json.loads(self.config_path.read_text(encoding="utf-8"))
        except FileNotFoundError as error:
            raise TenderWorkflowError("Tender workflow configuration is unavailable.") from error
        except json.JSONDecodeError as error:
            raise TenderWorkflowError("Tender workflow configuration is invalid JSON.") from error

    def _source_path(self, source_key: str) -> Path:
        source_name = self._config()["source_files"].get(source_key)
        if not source_name:
            raise TenderWorkflowError(f"Unknown tender source: {source_key}.")
        path = self.data2_dir / source_name
        if not path.is_file():
            raise TenderWorkflowError(f"Required tender source is unavailable: {source_name}.")
        return path

    def _checklists_by_key(self) -> dict[str, dict[str, Any]]:
        return {item["key"]: item for item in self._config().get("checklists", [])}

    def _actions_by_key(self) -> dict[str, dict[str, Any]]:
        return {item["key"]: item for item in self._config().get("workflow", {}).get("actions", [])}

    def _statuses_by_key(self) -> dict[str, str]:
        return {item["key"]: item["label"] for item in self._config().get("workflow", {}).get("statuses", [])}

    def _read_csv(self, source_key: str) -> list[dict[str, str]]:
        path = self._source_path(source_key)
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                return list(csv.DictReader(handle))
        except UnicodeDecodeError:
            with path.open("r", encoding="latin-1", newline="") as handle:
                return list(csv.DictReader(handle))

    def _read_workbook(self) -> list[dict[str, Any]]:
        """Read cached workbook values without changing the supplied workbook.

        The application only uses cached values and labels from the workbook. It
        never overwrites formulas or treats a formula reference as an approval.
        """
        path = self._source_path("calculation_workbook")
        main_ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
        rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
        document_rel_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        with zipfile.ZipFile(path) as archive:
            shared: list[str] = []
            if "xl/sharedStrings.xml" in archive.namelist():
                root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
                for item in root.findall(f"{{{main_ns}}}si"):
                    shared.append("".join(node.text or "" for node in item.iter(f"{{{main_ns}}}t")))
            workbook = ET.fromstring(archive.read("xl/workbook.xml"))
            relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            targets = {item.attrib["Id"]: item.attrib["Target"] for item in relationships.findall(f"{{{rel_ns}}}Relationship")}
            sheets: list[dict[str, Any]] = []
            for sheet in workbook.find(f"{{{main_ns}}}sheets") or []:
                relationship_id = sheet.attrib.get(f"{{{document_rel_ns}}}id")
                target = targets.get(relationship_id, "")
                if target.startswith("/"):
                    target = target.lstrip("/")
                elif not target.startswith("xl/"):
                    target = f"xl/{target}"
                if target not in archive.namelist():
                    continue
                sheet_root = ET.fromstring(archive.read(target))
                cells: dict[str, str] = {}
                for cell in sheet_root.findall(f".//{{{main_ns}}}sheetData/{{{main_ns}}}row/{{{main_ns}}}c"):
                    value_node = cell.find(f"{{{main_ns}}}v")
                    inline_node = cell.find(f"{{{main_ns}}}is")
                    value = ""
                    if inline_node is not None:
                        value = "".join(node.text or "" for node in inline_node.iter(f"{{{main_ns}}}t"))
                    elif value_node is not None:
                        value = value_node.text or ""
                        if cell.attrib.get("t") == "s" and value.isdigit():
                            value = shared[int(value)] if int(value) < len(shared) else ""
                    cells[cell.attrib.get("r", "")] = value
                sheets.append({"name": sheet.attrib.get("name", ""), "cells": cells})
            return sheets

    @staticmethod
    def _workbook_rows(sheet: dict[str, Any]) -> dict[int, dict[int, str]]:
        rows: dict[int, dict[int, str]] = {}
        for reference, value in sheet.get("cells", {}).items():
            match = re.match(r"^([A-Z]+)(\d+)$", reference)
            if not match:
                continue
            letters, row_number = match.groups()
            column_number = 0
            for letter in letters:
                column_number = column_number * 26 + ord(letter) - 64
            rows.setdefault(int(row_number), {})[column_number] = value
        return rows

    @staticmethod
    def _number(value: Any) -> float | None:
        text = str(value or "").replace(",", "").strip()
        try:
            number = float(text)
            return number if math.isfinite(number) else None
        except (TypeError, ValueError):
            return None

    def _workbook_value_after(self, rows: dict[int, dict[int, str]], pattern: str, numeric: bool = False) -> str:
        expression = re.compile(pattern, re.IGNORECASE)
        for row in rows.values():
            ordered = sorted(row.items())
            for index, (_, value) in enumerate(ordered):
                if not expression.search(str(value or "")):
                    continue
                candidates = [
                    candidate for _, candidate in ordered[index + 1:]
                    if str(candidate or "").strip() and str(candidate).strip() not in {":", "="}
                ]
                if numeric:
                    for candidate in candidates:
                        if self._number(candidate) is not None:
                            return str(candidate).strip()
                elif candidates:
                    return str(candidates[0]).strip()
        return ""

    def workbook_scenarios(self) -> list[dict[str, Any]]:
        scenarios: list[dict[str, Any]] = []
        for sheet in self._read_workbook():
            rows = self._workbook_rows(sheet)
            all_text = " ".join(value for row in rows.values() for value in row.values())
            years = re.search(r"FOR\s+(\d+)\s+YEARS", all_text, re.IGNORECASE)
            scenario = {
                "sheet": sheet["name"],
                "plot_name": self._workbook_value_after(rows, r"Plot No:", numeric=False),
                "area_sqm": self._workbook_value_after(rows, r"PLOT AREA", numeric=True),
                "lease_years": years.group(1) if years else "",
                "fsi": self._workbook_value_after(rows, r"^FSI$", numeric=True),
                "ready_reckoner_zone": self._workbook_value_after(rows, r"ZONE AS PER READY RECKONER", numeric=False),
                "sor_rate": self._workbook_value_after(rows, r"RATE (?:PER SQ\.\s*MTR\.\s*PER MONTH|AS PER SOR)", numeric=True),
                "discount_rate_percent": self._workbook_value_after(rows, r"Discounting Factor", numeric=True),
                "source_file": self._source_path("calculation_workbook").name,
            }
            scenarios.append(scenario)
        return scenarios

    def _workbook_matches(self, vacant_row: dict[str, str]) -> list[dict[str, Any]]:
        vacant_text = " ".join(str(v or "") for v in vacant_row.values()).casefold()
        vacant_area = self._number(vacant_row.get("area"))
        matches = []
        for scenario in self.workbook_scenarios():
            scenario_text = str(scenario.get("plot_name", "")).casefold().strip()
            scenario_area = self._number(scenario.get("area_sqm"))
            name_match = bool(scenario_text and scenario_text in vacant_text)
            area_match = vacant_area is not None and scenario_area is not None and abs(vacant_area - scenario_area) < 0.01
            if name_match or area_match:
                matches.append({**scenario, "match_basis": "plot text" if name_match else "exact area"})
        return matches

    def _load_records(self) -> list[dict[str, Any]]:
        if not self.storage_path.exists():
            return []
        try:
            content = json.loads(self.storage_path.read_text(encoding="utf-8"))
            return content if isinstance(content, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def _save_records(self, records: list[dict[str, Any]]) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.storage_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.storage_path)

    def _eligible_vacant_rows(self) -> list[dict[str, str]]:
        source = self._config().get("plot_source", {})
        source_key = source.get("source_key")
        eligibility_field = source.get("eligibility_field")
        eligible_values = {self._normalise(value) for value in source.get("eligible_values", [])}
        if not source_key or not eligibility_field or not eligible_values:
            raise TenderWorkflowError("Tender plot-source configuration is incomplete.")
        return [
            row
            for row in self._read_csv(source_key)
            if self._normalise(row.get(eligibility_field)) in eligible_values
        ]

    def _plot_id(self, row: dict[str, str]) -> str:
        field = self._config().get("plot_source", {}).get("id_field")
        value = str(row.get(field, "") if field else "").strip()
        if not value:
            raise TenderWorkflowError("Tender plot source has a record without its configured identifier.")
        return value

    def _plot_label(self, row: dict[str, str]) -> str:
        fields = self._config().get("plot_source", {}).get("display_fields", [])
        values = [str(row.get(field, "")).strip() for field in fields]
        return " · ".join(value for value in values if value)

    def list_plots(self) -> list[dict[str, Any]]:
        plots: list[dict[str, Any]] = []
        for row in self._eligible_vacant_rows():
            plots.append(
                {
                    "id": self._plot_id(row),
                    "label": self._plot_label(row) or f"Vacant plot {self._plot_id(row)}",
                    "plot_code": row.get("plot_code", ""),
                    "area_sqm": row.get("plot_area_sqm", ""),
                    "source_status": row.get("plot_status", ""),
                }
            )
        return plots

    def _vacant_plot(self, plot_id: str) -> dict[str, str]:
        requested_id = str(plot_id).strip()
        row = next((item for item in self._eligible_vacant_rows() if self._plot_id(item) == requested_id), None)
        if not row:
            raise TenderWorkflowError("The selected vacant plot is no longer eligible.")
        return row

    def _match_plot_master(self, vacant_row: dict[str, str]) -> dict[str, Any]:
        return {
            "status": "source_record",
            "matches": [{
                "plot_id": self._plot_id(vacant_row),
                "plot_code": vacant_row.get("plot_code", ""),
                "plot_name": vacant_row.get("main_structure_name", ""),
                "location": vacant_row.get("location", ""),
            }],
            "reason": "Plot context is sourced directly from the public-database export; no cross-file matching is used.",
        }

    @staticmethod
    def _table_rows_from_markdown(path: Path) -> list[dict[str, str]]:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        rows: list[dict[str, str]] = []
        collecting = False
        for line in lines:
            text = line.strip()
            if text.startswith("| Sr. No.") and "Check" in text:
                collecting = True
                continue
            if not collecting:
                continue
            if not text.startswith("|"):
                if rows:
                    break
                continue
            if re.match(r"^\|[\s|:-]+\|$", text):
                continue
            cells = [cell.strip().replace("<br>", " ") for cell in text.strip("|").split("|")]
            if len(cells) < 2:
                continue
            number, checkpoint = cells[0], cells[1]
            if not number or not checkpoint:
                continue
            rows.append(
                {
                    "key": f"item_{len(rows) + 1}",
                    "number": number,
                    "label": checkpoint,
                    "source_answer": cells[2] if len(cells) > 2 else "",
                    "source_remarks": cells[3] if len(cells) > 3 else "",
                }
            )
        return rows

    @staticmethod
    def _checklist_header_values(path: Path) -> dict[str, str]:
        values: dict[str, str] = {}
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lstrip().startswith("|") or line.startswith("### Table"):
                break
            if ":" not in line:
                continue
            label, value = line.split(":", 1)
            label = re.sub(r"\s+", " ", label).strip().casefold()
            value = re.sub(r"\s+", " ", value).strip()
            if label and value:
                values[label] = value
        return values

    def checklist(self, checklist_key: str) -> dict[str, Any]:
        checklist = self._checklists_by_key().get(checklist_key)
        if not checklist:
            raise TenderWorkflowError("Select a valid LAC checklist.")
        path = self._source_path(checklist["source_key"])
        header_values = self._checklist_header_values(path)
        prefill_fields: dict[str, str] = {}
        tender_method = header_values.get("proposed for govt. organization") or header_values.get("proposed for govt organization")
        if tender_method:
            prefill_fields["tender_method"] = tender_method
        return {
            "key": checklist_key,
            "label": checklist["label"],
            "source_file": path.name,
            "header_values": header_values,
            "prefill_fields": prefill_fields,
            "items": self._table_rows_from_markdown(path),
        }

    def config_payload(self) -> dict[str, Any]:
        config = self._config()
        return {
            "version": config.get("version"),
            "source_files": config.get("source_files", {}),
            "form_fields": config.get("form_fields", []),
            "checklists": [{"key": item["key"], "label": item["label"]} for item in config.get("checklists", [])],
            "statuses": self._statuses_by_key(),
            "workflow_notice": "Source data is used for plot context and checklist evidence. Approved commercial and policy values remain required workflow inputs.",
        }

    def plot_detail(self, plot_id: str) -> dict[str, Any]:
        row = self._vacant_plot(plot_id)
        mapping = self._match_plot_master(row)
        source = self._config().get("plot_source", {})
        source_snapshot = {key: row.get(key, "") for key in source.get("snapshot_fields", [])}
        prefill_fields = {
            target_field: row.get(source_field, "")
            for target_field, source_field in source.get("prefill_fields", {}).items()
            if row.get(source_field, "") not in (None, "")
        }
        return {
            "id": str(plot_id),
            "label": self._plot_label(row),
            "prefill_fields": prefill_fields,
            "source_snapshot": source_snapshot,
            "mapping": mapping,
            "workbook_matches": [],
            "workbook_prefill_status": "Case-example workbook values are not copied into a new tender workflow.",
            "rate_notice": "No approved current SoR/rate record is available in the public export. Enter or import an approved case-specific rate before calculating.",
        }

    def _field_definitions(self) -> dict[str, dict[str, Any]]:
        return {field["key"]: field for field in self._config().get("form_fields", [])}

    def _sanitize_fields(self, fields: dict[str, Any] | None) -> dict[str, Any]:
        definitions = self._field_definitions()
        clean: dict[str, Any] = {}
        for key, value in (fields or {}).items():
            if key not in definitions:
                continue
            if definitions[key].get("type") == "number":
                if value is None or str(value).strip() == "":
                    clean[key] = ""
                else:
                    clean[key] = self._clean_number(value, definitions[key]["label"])
            else:
                clean[key] = str(value or "").strip()
        return clean

    def calculate(self, fields: dict[str, Any]) -> dict[str, Any]:
        definitions = self._field_definitions()
        required_keys = ("area_sqm", "lease_years", "fsi", "approved_monthly_sor_rate", "annual_escalation_percent", "discount_rate_percent", "gst_percent")
        missing = [definitions[key]["label"] for key in required_keys if fields.get(key) in (None, "")]
        if missing:
            return {"ready": False, "missing_fields": missing, "steps": []}

        area = self._clean_number(fields["area_sqm"], definitions["area_sqm"]["label"], positive=True)
        lease_years = self._clean_number(fields["lease_years"], definitions["lease_years"]["label"], positive=True)
        if not lease_years.is_integer():
            raise TenderWorkflowError("Lease period must be a whole number of years.")
        fsi = self._clean_number(fields["fsi"], definitions["fsi"]["label"], positive=True)
        monthly_rate = self._clean_number(fields["approved_monthly_sor_rate"], definitions["approved_monthly_sor_rate"]["label"], positive=True)
        escalation = self._clean_number(fields["annual_escalation_percent"], definitions["annual_escalation_percent"]["label"])
        discount = self._clean_number(fields["discount_rate_percent"], definitions["discount_rate_percent"]["label"])
        gst = self._clean_number(fields["gst_percent"], definitions["gst_percent"]["label"])
        developed_area = area * fsi
        base_monthly_rent = developed_area * monthly_rate
        base_annual_rent = base_monthly_rent * 12
        npv_total = 0.0
        schedule: list[dict[str, float | int]] = []
        for year in range(1, int(lease_years) + 1):
            annual_rent = base_annual_rent * ((1 + escalation / 100) ** (year - 1))
            discount_factor = 1 / ((1 + discount / 100) ** (year - 1))
            present_value = annual_rent * discount_factor
            npv_total += present_value
            schedule.append({"year": year, "annual_rent": annual_rent, "discount_factor": discount_factor, "present_value": present_value})
        gst_amount = npv_total * gst / 100
        extras: dict[str, float] = {}
        for key in ("service_charge_per_sqm_year", "nominal_rent_per_sqm_year"):
            if fields.get(key) not in (None, ""):
                extras[key] = area * self._clean_number(fields[key], definitions[key]["label"])
        return {
            "ready": True,
            "currency": "INR",
            "developed_area_sqm": developed_area,
            "base_monthly_rent": base_monthly_rent,
            "base_annual_rent": base_annual_rent,
            "upfront_premium_before_gst": npv_total,
            "gst_amount": gst_amount,
            "upfront_premium_including_gst": npv_total + gst_amount,
            "annual_optional_charges": extras,
            "schedule": schedule,
            "steps": [
                "Developed area = plot area × approved FSI.",
                "Base annual rent = developed area × approved monthly SoR rate × 12.",
                "Each lease-year rent is escalated by the approved annual escalation percentage.",
                "Each year is discounted using the approved discount rate; the upfront premium is the sum of those present values.",
                "GST is calculated from the resulting upfront premium using the entered approved percentage.",
            ],
            "source_references": [self._config()["source_files"]["upfront_calculation_reference"], self._config()["source_files"]["npv_calculation_reference"]],
        }

    def _hydrate(self, record: dict[str, Any]) -> dict[str, Any]:
        output = json.loads(json.dumps(record))
        output["status_label"] = self._statuses_by_key().get(output.get("status"), output.get("status"))
        output["available_actions"] = [
            {"key": key, "label": action["label"]}
            for key, action in self._actions_by_key().items()
            if output.get("status") in action.get("from", [])
        ]
        return output

    def list_workflows(self) -> list[dict[str, Any]]:
        with self._lock:
            return [self._hydrate(record) for record in sorted(self._load_records(), key=lambda item: item.get("updated_at", ""), reverse=True)]

    def get_workflow(self, workflow_id: str) -> dict[str, Any]:
        with self._lock:
            for record in self._load_records():
                if record.get("id") == workflow_id:
                    return self._hydrate(record)
        raise TenderWorkflowError("Tender workflow was not found.")

    def _checklist_answers(self, checklist: dict[str, Any], answers: dict[str, Any] | None) -> list[dict[str, str]]:
        supplied = answers or {}
        return [
            {
                **item,
                "answer": str(supplied.get(item["key"], item.get("source_answer", "")) or "").strip(),
            }
            for item in checklist["items"]
        ]

    def create_workflow(self, payload: dict[str, Any]) -> dict[str, Any]:
        plot_id = str(payload.get("plot_id", ""))
        checklist_key = str(payload.get("checklist_key", ""))
        detail = self.plot_detail(plot_id)
        checklist = self.checklist(checklist_key)
        fields = self._sanitize_fields(payload.get("fields"))
        for key, value in checklist.get("prefill_fields", {}).items():
            if fields.get(key) in (None, ""):
                fields[key] = value
        if not fields.get("area_sqm") and detail["prefill_fields"].get("area_sqm"):
            fields["area_sqm"] = self._clean_number(detail["prefill_fields"]["area_sqm"], "Area")
        now = self._now()
        record = {
            "id": uuid.uuid4().hex,
            "status": self._config().get("workflow", {}).get("initial_status", "LAC_DRAFT"),
            "plot_id": plot_id,
            "plot_label": detail["label"],
            "source_snapshot": detail["source_snapshot"],
            "plot_mapping": detail["mapping"],
            "checklist": {"key": checklist["key"], "label": checklist["label"], "source_file": checklist["source_file"], "items": self._checklist_answers(checklist, payload.get("checklist_answers"))},
            "fields": fields,
            "calculation": self.calculate(fields),
            "created_at": now,
            "updated_at": now,
            "events": [{"at": now, "action": "created", "from": None, "to": self._config().get("workflow", {}).get("initial_status", "LAC_DRAFT"), "comment": "Workflow draft created."}],
        }
        with self._lock:
            records = self._load_records()
            records.append(record)
            self._save_records(records)
        return self._hydrate(record)

    def _merge_inputs(self, record: dict[str, Any], fields: dict[str, Any] | None, checklist_answers: dict[str, Any] | None) -> None:
        record["fields"].update(self._sanitize_fields(fields))
        answers = checklist_answers or {}
        for item in record["checklist"]["items"]:
            if item["key"] in answers:
                item["answer"] = str(answers[item["key"]] or "").strip()
        record["calculation"] = self.calculate(record["fields"])

    def _validate_action(self, record: dict[str, Any], action_key: str, action: dict[str, Any], comment: str) -> None:
        requirements = set(action.get("requires", []))
        if "comment" in requirements and not comment.strip():
            raise TenderWorkflowError("A return comment is required.")
        if "lac_complete" in requirements:
            missing_answers = [item["number"] for item in record["checklist"]["items"] if not item.get("answer", "").strip()]
            if missing_answers:
                raise TenderWorkflowError(f"Complete every LAC checklist response before submission (missing: {', '.join(missing_answers)}).")
            required_fields = [
                field["label"]
                for field in self._config().get("form_fields", [])
                if action_key in field.get("required_for", []) and not record["fields"].get(field["key"])
            ]
            if required_fields:
                raise TenderWorkflowError(f"Complete required LAC fields: {', '.join(required_fields)}.")
        if "proposal_fields" in requirements:
            missing = [
                field["label"]
                for field in self._config().get("form_fields", [])
                if action_key in field.get("required_for", []) and not record["fields"].get(field["key"])
            ]
            if missing:
                raise TenderWorkflowError(f"Complete required proposal fields: {', '.join(missing)}.")
        if "calculation" in requirements and not record["calculation"].get("ready"):
            raise TenderWorkflowError("Complete the approved financial inputs before finalizing the calculation.")

    def apply_action(self, workflow_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        action_key = str(payload.get("action", ""))
        config = self._config()
        action = self._actions_by_key().get(action_key)
        if not action:
            raise TenderWorkflowError("Unknown workflow action.")
        comment = str(payload.get("comment", "") or "").strip()
        with self._lock:
            records = self._load_records()
            record = next((item for item in records if item.get("id") == workflow_id), None)
            if not record:
                raise TenderWorkflowError("Tender workflow was not found.")
            if record.get("status") not in action.get("from", []):
                raise TenderWorkflowError("This action is not available at the current workflow stage.")
            self._merge_inputs(record, payload.get("fields"), payload.get("checklist_answers"))
            self._validate_action(record, action_key, action, comment)
            before = record["status"]
            record["status"] = action["to"]
            record["updated_at"] = self._now()
            record["events"].append({"at": record["updated_at"], "action": action_key, "from": before, "to": record["status"], "comment": comment})
            self._save_records(records)
            return self._hydrate(record)

    @staticmethod
    def _money(value: Any) -> str:
        try:
            return f"INR {float(value):,.2f}"
        except (TypeError, ValueError):
            return "Not available"

    def document_markdown(self, workflow_id: str, kind: str) -> str:
        if kind not in {"lac", "board-note", "tender"}:
            raise TenderWorkflowError("Document type must be lac, board-note, or tender.")
        workflow = self.get_workflow(workflow_id)
        source_files = self._config()["source_files"]
        title = {"lac": "LAC Proposal Draft", "board-note": "Board Note Draft", "tender": "Tender Draft"}[kind]
        template_key = {"lac": "embarkation_checklist", "board-note": "board_note_template", "tender": "tender_template"}[kind]
        lines = [
            f"# {title}",
            "",
            "> Draft generated from the Tender Publication workflow record. It is not an approved or publishable document until the required authority approvals and template review are complete.",
            "",
            "## Workflow record",
            "",
            f"- **Workflow ID:** `{workflow['id']}`",
            f"- **Current stage:** {workflow['status_label']}",
            f"- **Selected plot:** {workflow['plot_label']}",
            f"- **Source template/reference:** `{source_files[template_key]}`",
            "",
            "## Source-backed plot context",
            "",
        ]
        for key, value in workflow["source_snapshot"].items():
            if value not in (None, ""):
                lines.append(f"- **{key.replace('_', ' ').title()}:** {value}")
        lines.extend(["", "## Entered proposal inputs", ""])
        for field in self._config().get("form_fields", []):
            value = workflow["fields"].get(field["key"], "")
            if value not in (None, ""):
                lines.append(f"- **{field['label']}:** {value}")
        if kind == "lac":
            lines.extend(["", "## LAC checklist responses", "", "| No. | Check point | Response |", "| --- | --- | --- |"])
            for item in workflow["checklist"]["items"]:
                label = item["label"].replace("|", "/")
                answer = item.get("answer", "").replace("|", "/")
                lines.append(f"| {item['number']} | {label} | {answer} |")
        calculation = workflow.get("calculation", {})
        if calculation.get("ready"):
            lines.extend(
                [
                    "",
                    "## Financial calculation draft",
                    "",
                    f"- **Developed area:** {float(calculation['developed_area_sqm']):,.2f} sq. m",
                    f"- **Base monthly rent:** {self._money(calculation['base_monthly_rent'])}",
                    f"- **Base annual rent:** {self._money(calculation['base_annual_rent'])}",
                    f"- **Upfront premium before GST:** {self._money(calculation['upfront_premium_before_gst'])}",
                    f"- **GST amount:** {self._money(calculation['gst_amount'])}",
                    f"- **Upfront premium including GST:** {self._money(calculation['upfront_premium_including_gst'])}",
                    "",
                    "Calculation uses the approved values entered in this workflow; source reference files are listed below and must be reviewed by the approving authority.",
                ]
            )
        else:
            lines.extend(["", "## Financial calculation draft", "", "Calculation is pending required approved inputs: " + ", ".join(calculation.get("missing_fields", [])) + "."])
        lines.extend(["", "## Source references", ""])
        for source in calculation.get("source_references", []) if isinstance(calculation, dict) else []:
            lines.append(f"- `{source}`")
        lines.extend(["", "## Workflow history", "", "| Time (UTC) | Action | From | To | Comment |", "| --- | --- | --- | --- | --- |"])
        for event in workflow.get("events", []):
            lines.append(f"| {event['at']} | {event['action']} | {event.get('from') or ''} | {event.get('to') or ''} | {event.get('comment', '').replace('|', '/')} |")
        return "\n".join(lines) + "\n"

    def document_pdf(self, workflow_id: str, kind: str) -> bytes:
        """Render a downloaded workflow document as a formatted PDF."""
        if kind not in {"lac", "board-note", "tender"}:
            raise TenderWorkflowError("Document type must be lac, board-note, or tender.")
        try:
            from workflows.tender_document_pdf import build_tender_document_pdf

            return build_tender_document_pdf(self.get_workflow(workflow_id), self._config(), kind)
        except ImportError as error:
            raise TenderWorkflowError("PDF generation dependency is unavailable. Install the project requirements and restart the server.") from error
