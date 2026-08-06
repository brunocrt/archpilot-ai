import unittest
from pathlib import Path


API_ROOT = Path(__file__).resolve().parents[2]
BASELINE_MIGRATION = API_ROOT / "migrations" / "versions" / "0001_baseline_schema.py"


class MigrationTests(unittest.TestCase):
    def test_startup_db_init_does_not_mutate_schema(self) -> None:
        db_source = (API_ROOT / "app" / "db.py").read_text()

        self.assertNotIn("create_all", db_source)
        self.assertNotIn("ALTER TABLE", db_source.upper())

    def test_baseline_migration_includes_pgvector_schema(self) -> None:
        migration_source = BASELINE_MIGRATION.read_text()

        self.assertIn("CREATE EXTENSION IF NOT EXISTS vector", migration_source)
        self.assertIn("Vector(1536)", migration_source)
        self.assertIn("ix_document_chunks_embedding_hnsw", migration_source)

    def test_baseline_migration_includes_required_indexes(self) -> None:
        migration_source = BASELINE_MIGRATION.read_text()
        expected_indexes = [
            "ix_documents_project_id",
            "ix_documents_filename",
            "ix_documents_content_type",
            "ix_messages_conversation_id",
            "ix_retrieval_logs_message_id",
            "ix_retrieval_logs_chunk_id",
        ]

        for index_name in expected_indexes:
            with self.subTest(index_name=index_name):
                self.assertIn(index_name, migration_source)


if __name__ == "__main__":
    unittest.main()
