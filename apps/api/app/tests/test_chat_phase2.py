import unittest
from uuid import uuid4

from app.api.chat import persist_retrieval_diagnostics, retrieval_diagnostics
from app.domain.schemas import ChatQuery, RetrievedChunk
from app.services.llm_gateway import LLMGateway
from app.services.prompt_service import build_prompt


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

    def test_persist_retrieval_diagnostics_records_ranked_entries(self) -> None:
        class FakeConversationRepository:
            def __init__(self) -> None:
                self.entries = []

            def add_retrieval_logs(self, message_id, entries):
                self.message_id = message_id
                self.entries = entries

        project_id = uuid4()
        assistant_message_id = uuid4()
        payload = ChatQuery(
            question="Why modular monolith?",
            project_id=str(project_id),
            document_filename="adr",
            content_type="text/markdown",
            top_k=2,
        )
        chunks = [
            RetrievedChunk(
                chunk_id=str(uuid4()),
                document_id=str(uuid4()),
                document_filename="adr.md",
                chunk_index=0,
                score=0.91,
                retrieval_signal="hybrid",
                content="Use a modular monolith.",
            )
        ]
        diagnostics = retrieval_diagnostics(payload, project_id, chunks, retrieval_latency_ms=12.5)
        repo = FakeConversationRepository()

        persist_retrieval_diagnostics(
            repo,  # type: ignore[arg-type]
            assistant_message_id,
            payload,
            project_id,
            chunks,
            diagnostics,
        )

        self.assertEqual(assistant_message_id, repo.message_id)
        self.assertEqual(1, len(repo.entries))
        self.assertEqual(1, repo.entries[0]["rank"])
        self.assertEqual("hybrid", repo.entries[0]["retrieval_signal"])
        self.assertEqual(12.5, repo.entries[0]["retrieval_latency_ms"])
        self.assertEqual(str(project_id), repo.entries[0]["applied_filters"]["project_id"])


if __name__ == "__main__":
    unittest.main()
