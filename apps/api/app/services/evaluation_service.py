"""
Evaluation service placeholder.

This module defines a minimal interface for logging retrieval and answer
quality.  In a production system, this could run automated checks on
answers (e.g., grounding detection, hallucination risk) and compute
metrics.  For the MVP we simply record feedback provided by users.
"""
from __future__ import annotations

from typing import Optional


class EvaluationService:
    def evaluate(self, question: str, answer: str, context: str) -> Optional[dict]:
        """Evaluate the answer quality.

        :return: Optional metrics dictionary.  Currently returns None.
        """
        # Placeholder implementation; could compute ROUGE, grounding, etc.
        return None