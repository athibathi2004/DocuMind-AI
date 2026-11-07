from typing import List, Dict, Any, Tuple, Optional
from app.models.document import DocumentCategory
from app.models.validation import ValidationRuleStatus
from app.models.extraction import ValidationStatus
from app.extraction.base import RawExtractedField
from app.validation.mrz_validator import default_mrz_validator
from app.validation.field_rules import (
    REQUIRED_FIELDS_BY_CATEGORY,
    normalize_date,
    validate_numeric_amount,
    check_invoice_math,
    check_passport_dates,
)


class ValidationEngine:
    """
    Executes comprehensive syntactic, semantic, and cross-field validation.
    Does not make false claims regarding document physical authenticity.
    """

    def validate_document_fields(
        self,
        category: DocumentCategory,
        fields: List[RawExtractedField],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, ValidationStatus], Dict[str, str]]:
        """
        Executes all validation checks for the given category and extracted fields.
        Returns:
            - validation_results: List of dicts representing rule execution outcomes.
            - field_statuses: Mapping of field_name -> ValidationStatus.
            - normalized_values: Mapping of field_name -> normalized string value.
        """
        validation_results: List[Dict[str, Any]] = []
        field_statuses: Dict[str, ValidationStatus] = {}
        normalized_values: Dict[str, str] = {}

        field_map = {f.field_name: f for f in fields}

        # 1. Required Field Checks
        required_fields = REQUIRED_FIELDS_BY_CATEGORY.get(category, set())
        for req_field in required_fields:
            field = field_map.get(req_field)
            if not field or field.is_missing or not field.field_value:
                validation_results.append({
                    "rule_name": f"REQUIRED_{req_field.upper()}",
                    "rule_type": "REQUIRED_FIELD",
                    "field_name": req_field,
                    "status": ValidationRuleStatus.FAIL,
                    "message": f"Mandatory field '{req_field}' is missing from document.",
                    "details": {"required": True, "present": False},
                })
                field_statuses[req_field] = ValidationStatus.MISSING
            else:
                validation_results.append({
                    "rule_name": f"REQUIRED_{req_field.upper()}",
                    "rule_type": "REQUIRED_FIELD",
                    "field_name": req_field,
                    "status": ValidationRuleStatus.PASS,
                    "message": f"Required field '{req_field}' is present.",
                    "details": {"required": True, "present": True},
                })

        # 2. Field-level Type & Format Validation
        for f in fields:
            name = f.field_name
            val = f.field_value

            if f.is_missing or val is None:
                if name not in field_statuses:
                    field_statuses[name] = ValidationStatus.MISSING
                continue

            status = ValidationStatus.VALID

            # Date fields
            if f.field_type == "date" or "date" in name:
                valid_date, iso_date, err = normalize_date(val)
                if valid_date and iso_date:
                    normalized_values[name] = iso_date
                    validation_results.append({
                        "rule_name": f"FORMAT_DATE_{name.upper()}",
                        "rule_type": "FORMAT_CHECK",
                        "field_name": name,
                        "status": ValidationRuleStatus.PASS,
                        "message": f"Date '{val}' normalized to ISO format '{iso_date}'.",
                        "details": {"original": val, "normalized": iso_date},
                    })
                else:
                    status = ValidationStatus.WARNING
                    validation_results.append({
                        "rule_name": f"FORMAT_DATE_{name.upper()}",
                        "rule_type": "FORMAT_CHECK",
                        "field_name": name,
                        "status": ValidationRuleStatus.WARNING,
                        "message": err or "Unrecognized date format.",
                        "details": {"original": val},
                    })

            # Numeric amounts
            elif f.field_type == "number" or name in ["subtotal", "tax", "total_amount"]:
                valid_num, num_val, err = validate_numeric_amount(val)
                if valid_num and num_val is not None:
                    normalized_values[name] = f"{num_val:.2f}"
                    validation_results.append({
                        "rule_name": f"NUMERIC_{name.upper()}",
                        "rule_type": "FORMAT_CHECK",
                        "field_name": name,
                        "status": ValidationRuleStatus.PASS,
                        "message": f"Numeric amount parsed successfully: {num_val:.2f}.",
                        "details": {"original": val, "parsed": num_val},
                    })
                else:
                    status = ValidationStatus.INVALID
                    validation_results.append({
                        "rule_name": f"NUMERIC_{name.upper()}",
                        "rule_type": "FORMAT_CHECK",
                        "field_name": name,
                        "status": ValidationRuleStatus.FAIL,
                        "message": err or "Invalid numeric format.",
                        "details": {"original": val},
                    })

            if name not in field_statuses or field_statuses[name] == ValidationStatus.VALID:
                field_statuses[name] = status

        # 3. Cross-Field Checks
        if category == DocumentCategory.INVOICE:
            sub_val = None
            tax_val = None
            tot_val = None

            if "subtotal" in normalized_values:
                sub_val = float(normalized_values["subtotal"])
            if "tax" in normalized_values:
                tax_val = float(normalized_values["tax"])
            if "total_amount" in normalized_values:
                tot_val = float(normalized_values["total_amount"])

            if sub_val is not None and tot_val is not None:
                math_valid, math_err = check_invoice_math(sub_val, tax_val, tot_val)
                if math_valid:
                    validation_results.append({
                        "rule_name": "INVOICE_TOTALS_CONSISTENCY",
                        "rule_type": "CROSS_FIELD",
                        "field_name": "total_amount",
                        "status": ValidationRuleStatus.PASS,
                        "message": f"Invoice arithmetic checks out: {sub_val:.2f} + {tax_val or 0:.2f} == {tot_val:.2f}.",
                        "details": {"subtotal": sub_val, "tax": tax_val, "total": tot_val},
                    })
                else:
                    validation_results.append({
                        "rule_name": "INVOICE_TOTALS_CONSISTENCY",
                        "rule_type": "CROSS_FIELD",
                        "field_name": "total_amount",
                        "status": ValidationRuleStatus.FAIL,
                        "message": math_err,
                        "details": {"subtotal": sub_val, "tax": tax_val, "total": tot_val},
                    })
                    field_statuses["total_amount"] = ValidationStatus.INVALID

        elif category == DocumentCategory.PASSPORT:
            # Check dates
            dob_iso = normalized_values.get("date_of_birth")
            exp_iso = normalized_values.get("date_of_expiry")
            if dob_iso and exp_iso:
                dates_valid, dates_err = check_passport_dates(dob_iso, exp_iso)
                if dates_valid:
                    validation_results.append({
                        "rule_name": "PASSPORT_DATE_CHRONOLOGY",
                        "rule_type": "CROSS_FIELD",
                        "field_name": "date_of_expiry",
                        "status": ValidationRuleStatus.PASS,
                        "message": "Passport expiry date is chronologically after birth date.",
                        "details": {"birth": dob_iso, "expiry": exp_iso},
                    })
                else:
                    validation_results.append({
                        "rule_name": "PASSPORT_DATE_CHRONOLOGY",
                        "rule_type": "CROSS_FIELD",
                        "field_name": "date_of_expiry",
                        "status": ValidationRuleStatus.FAIL,
                        "message": dates_err or "Invalid date sequence.",
                        "details": {"birth": dob_iso, "expiry": exp_iso},
                    })
                    field_statuses["date_of_expiry"] = ValidationStatus.INVALID

            # MRZ Check digits
            mrz2_field = field_map.get("mrz_line2")
            if mrz2_field and mrz2_field.field_value:
                mrz_out = default_mrz_validator.validate_td3_line2(mrz2_field.field_value)
                if mrz_out["is_valid"]:
                    validation_results.append({
                        "rule_name": "PASSPORT_MRZ_CHECKSUM",
                        "rule_type": "MRZ_CHECKSUM",
                        "field_name": "mrz_line2",
                        "status": ValidationRuleStatus.PASS,
                        "message": "ICAO 9303 Part 9 check digits verified (document number, birth date, expiry, composite).",
                        "details": mrz_out["checks"],
                    })
                else:
                    validation_results.append({
                        "rule_name": "PASSPORT_MRZ_CHECKSUM",
                        "rule_type": "MRZ_CHECKSUM",
                        "field_name": "mrz_line2",
                        "status": ValidationRuleStatus.FAIL,
                        "message": mrz_out.get("error") or "MRZ checksum mismatch.",
                        "details": mrz_out.get("checks"),
                    })
                    field_statuses["mrz_line2"] = ValidationStatus.WARNING

        return validation_results, field_statuses, normalized_values


default_validation_engine = ValidationEngine()

