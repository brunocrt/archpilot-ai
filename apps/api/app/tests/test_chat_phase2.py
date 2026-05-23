import unittest

from app.api.chat import build_prompt
from app.domain.schemas import RetrievedChunk
from app.services.llm_gateway import LLMGateway


class ChatPhase2Tests(unittest.TestCase):
    def test_build_prompt_uses_user_question_template(self) -> None:
        prompt = build_prompt(
            "Why a modular monolith?",
            [
                RetrievedChunk(
                    chunk_id="chunk-1",
                    document_id="doc-1",
                    document_filename="adr.md",
                    chunk_index=0,
                    score=0.5,
                    content="Use a modular monolith.",
                )
            ],
        )

        self.assertIn("User question:", prompt)
        self.assertIn("Why a modular monolith?", prompt)
        self.assertIn("[chunk-1] Use a modular monolith.", prompt)

    def test_stream_fallback_chunks_preserve_answer_text(self) -> None:
        gateway = LLMGateway()
        answer = "This answer is split into smaller response chunks for streaming."

        self.assertEqual(answer, "".join(gateway._chunk_text(answer, size=4)))


if __name__ == "__main__":
    unittest.main()
