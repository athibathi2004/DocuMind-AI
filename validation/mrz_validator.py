import re
from typing import Dict, Any, Tuple, Optional


class MRZValidator:
    """
    Validates Machine Readable Zone (MRZ) strings according to
    ICAO Document 9303 Part 9 standards for TD3 travel documents (Passports).
    Note: Validates format and checksum mathematical integrity only.
    Does NOT assert document physical authenticity or legal validity.
    """

    WEIGHTS = [7, 3, 1]

    @classmethod
    def char_to_value(cls, ch: str) -> int:
        """Converts an MRZ character to its numeric value (0-9, A-Z -> 10-35, '<' -> 0)."""
        ch = ch.upper()
        if ch == "<" or ch == "0":
            return 0
        elif ch.isdigit():
            return int(ch)
        elif "A" <= ch <= "Z":
            return ord(ch) - ord("A") + 10
        return 0

    @classmethod
    def compute_check_digit(cls, text: str) -> int:
        """Computes ICAO 9303 check digit using repeating weights 7, 3, 1."""
        total = 0
        for i, ch in enumerate(text):
            weight = cls.WEIGHTS[i % len(cls.WEIGHTS)]
            val = cls.char_to_value(ch)
            total += val * weight
        return total % 10

    @classmethod
    def validate_td3_line2(cls, line2: str) -> Dict[str, Any]:
        """
        Validates check digits for a 44-character TD3 Line 2.
        Line 2 layout:
        - 0..8: Document Number (9 chars)
        - 9: Document Number Check Digit
        - 10..12: Nationality (3 chars)
        - 13..18: Date of Birth YYMMDD (6 chars)
        - 19: Date of Birth Check Digit
        - 20: Sex (1 char)
        - 21..26: Date of Expiry YYMMDD (6 chars)
        - 27: Date of Expiry Check Digit
        - 28..41: Optional Data (14 chars)
        - 42: Optional Data Check Digit
        - 43: Composite Check Digit
        """
        cleaned = line2.strip().replace(" ", "").upper()
        if len(cleaned) != 44:
            return {
                "is_valid": False,
                "error": f"Invalid TD3 MRZ Line 2 length: expected 44 characters, got {len(cleaned)}.",
                "checks": {},
            }

        checks: Dict[str, Dict[str, Any]] = {}

        # 1. Document Number
        doc_num_field = cleaned[0:9]
        doc_num_cd = cleaned[9]
        expected_doc_cd = str(cls.compute_check_digit(doc_num_field))
        checks["passport_number"] = {
            "value": doc_num_field.replace("<", ""),
            "actual_cd": doc_num_cd,
            "expected_cd": expected_doc_cd,
            "valid": doc_num_cd == expected_doc_cd,
        }

        # 2. Date of Birth
        dob_field = cleaned[13:19]
        dob_cd = cleaned[19]
        expected_dob_cd = str(cls.compute_check_digit(dob_field))
        checks["date_of_birth"] = {
            "value": dob_field,
            "actual_cd": dob_cd,
            "expected_cd": expected_dob_cd,
            "valid": dob_cd == expected_dob_cd,
        }

        # 3. Date of Expiry
        exp_field = cleaned[21:27]
        exp_cd = cleaned[27]
        expected_exp_cd = str(cls.compute_check_digit(exp_field))
        checks["date_of_expiry"] = {
            "value": exp_field,
            "actual_cd": exp_cd,
            "expected_cd": expected_exp_cd,
            "valid": exp_cd == expected_exp_cd,
        }

        # 4. Composite Check Digit
        # In TD3: computed over line2[0:10] + line2[13:20] + line2[21:43]
        composite_data = cleaned[0:10] + cleaned[13:20] + cleaned[21:43]
        composite_cd = cleaned[43]
        expected_composite_cd = str(cls.compute_check_digit(composite_data))
        checks["composite"] = {
            "actual_cd": composite_cd,
            "expected_cd": expected_composite_cd,
            "valid": composite_cd == expected_composite_cd,
        }

        all_valid = all(check["valid"] for check in checks.values())

        return {
            "is_valid": all_valid,
            "error": None if all_valid else "One or more MRZ checksum checks failed.",
            "checks": checks,
        }


default_mrz_validator = MRZValidator()

