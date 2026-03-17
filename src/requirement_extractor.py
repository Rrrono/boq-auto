"""Tender requirement extraction heuristics."""

from __future__ import annotations

import logging
import re

from .models import AppConfig
from .tender_models import TenderDocument, TenderRequirement


MANDATORY_TERMS = ("shall", "must", "mandatory", "required", "submit", "attach")
PERCENT_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\s*%")
MONEY_PATTERN = re.compile(r"\b(?:kes|kshs?|usd)\s*[\d,]+(?:\.\d+)?", re.IGNORECASE)
PERIOD_PATTERN = re.compile(r"\b\d+\s*(?:calendar\s+)?(?:days?|weeks?|months?)\b", re.IGNORECASE)


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _titleize(category_key: str) -> str:
    return category_key.replace("_", " ").strip().title()


class RequirementExtractor:
    """Extract review-first tender requirements from normalized text."""

    def __init__(self, config: AppConfig, logger: logging.Logger | None = None) -> None:
        self.config = config
        self.logger = logger
        self.categories: dict[str, dict[str, object]] = config.get("tender_analysis.requirement_categories", {})
        self.thresholds: dict[str, float] = config.get("tender_analysis.confidence_thresholds", {})
        self.default_owner = str(config.get("tender_analysis.default_owner", "Estimator"))
        self.review_status = str(config.get("tender_analysis.review_status", "pending review"))

    def extract(self, document: TenderDocument) -> list[TenderRequirement]:
        requirements: list[TenderRequirement] = []
        seen: set[tuple[str, str, str]] = set()
        medium_threshold = float(self.thresholds.get("medium", 70))

        for line in document.lines:
            normalized_line = _normalize(line.text)
            for category_key, category_settings in self.categories.items():
                phrases = [str(item).lower() for item in category_settings.get("phrases", [])]
                for phrase in phrases:
                    if phrase not in normalized_line:
                        continue
                    signature = (category_key, phrase, line.source_reference)
                    if signature in seen:
                        continue
                    seen.add(signature)

                    confidence = self._score_requirement(normalized_line, phrase)
                    detail = self._extract_detail(category_key, line.text)
                    mandatory = self._is_mandatory(normalized_line, category_key)
                    review_flag = confidence < medium_threshold or self._requires_detail_review(category_key, detail)
                    notes = self._build_notes(category_key, detail, review_flag)
                    action_needed = self._build_action(category_key, mandatory, detail)
                    owner = str(category_settings.get("owner", self.default_owner))
                    description = self._build_description(category_key, line.text, detail)
                    requirement_id = f"REQ-{len(requirements) + 1:03d}"
                    requirements.append(
                        TenderRequirement(
                            requirement_id=requirement_id,
                            category=_titleize(category_key),
                            description=description,
                            mandatory=mandatory,
                            source_reference=line.source_reference,
                            confidence=confidence,
                            action_needed=action_needed,
                            owner=owner,
                            status=self.review_status,
                            notes=notes,
                            matched_phrase=phrase,
                            extracted_text=line.text,
                            review_flag=review_flag,
                        )
                    )
                    break

        if self.logger:
            self.logger.info("Extracted %s tender requirement candidate(s).", len(requirements))
        return requirements

    def _score_requirement(self, normalized_line: str, phrase: str) -> float:
        confidence = 58.0
        if phrase == normalized_line:
            confidence += 18.0
        if phrase in normalized_line:
            confidence += 15.0
        if any(term in normalized_line for term in MANDATORY_TERMS):
            confidence += 12.0
        if PERCENT_PATTERN.search(normalized_line) or MONEY_PATTERN.search(normalized_line):
            confidence += 6.0
        if PERIOD_PATTERN.search(normalized_line):
            confidence += 6.0
        return min(confidence, 96.0)

    def _extract_detail(self, category_key: str, text: str) -> str:
        lowered = text.lower()
        if category_key == "securities":
            for pattern in (PERCENT_PATTERN, MONEY_PATTERN):
                match = pattern.search(text)
                if match:
                    return match.group(0)
            return ""
        if category_key == "periods":
            match = PERIOD_PATTERN.search(text)
            return match.group(0) if match else ""
        if category_key == "meetings":
            if "mandatory" in lowered:
                return "Mandatory meeting/site visit referenced"
            return "Meeting/site visit referenced"
        if category_key == "pricing_instructions":
            if "provisional sum" in lowered:
                return "Provisional sum pricing instruction"
            if "dayworks" in lowered:
                return "Dayworks pricing instruction"
            if "schedule of rates" in lowered:
                return "Schedule of rates referenced"
            return ""
        return ""

    def _is_mandatory(self, normalized_line: str, category_key: str) -> bool:
        if any(term in normalized_line for term in MANDATORY_TERMS):
            return True
        return category_key in {"submission_documents", "securities"}

    def _build_description(self, category_key: str, line_text: str, detail: str) -> str:
        if detail:
            return f"{_titleize(category_key)}: {detail}"
        return f"{_titleize(category_key)}: {line_text}"

    def _build_notes(self, category_key: str, detail: str, review_flag: bool) -> str:
        if not review_flag:
            return ""
        if not detail:
            return f"Review exact tender wording for {_titleize(category_key).lower()}."
        return "Review extracted detail against the tender source before submission."

    def _requires_detail_review(self, category_key: str, detail: str) -> bool:
        if category_key not in {"securities", "periods", "meetings", "pricing_instructions"}:
            return False
        return detail == ""

    def _build_action(self, category_key: str, mandatory: bool, detail: str) -> str:
        if category_key == "submission_documents":
            return "Confirm document is available and include it in submission pack."
        if category_key == "securities":
            return "Confirm instrument type, value, and issuing bank."
        if category_key == "meetings":
            return "Confirm attendance requirement and record evidence."
        if category_key == "periods":
            if detail:
                return f"Record period in tender tracker: {detail}."
            return "Confirm the governing completion, delivery, or validity period."
        if category_key == "pricing_instructions":
            return "Review pricing instruction before BOQ gap check and pricing."
        if mandatory:
            return "Confirm compliance before submission."
        return "Review and decide whether tender response action is needed."
