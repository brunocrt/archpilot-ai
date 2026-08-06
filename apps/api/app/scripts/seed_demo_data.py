"""Seed local demo/reference documents into ArchPilot."""
from __future__ import annotations

import argparse
import asyncio
import mimetypes
from pathlib import Path

from app.db import get_db
from app.domain import models
from app.repositories.document_repository import DocumentRepository
from app.repositories.project_repository import ProjectRepository
from app.utils.chunking import split_text
from app.utils.embeddings import get_embedding
from app.utils.parsing import parse_file_bytes


SUPPORTED_EXTENSIONS = {".json", ".md", ".markdown", ".pdf", ".txt"}


async def seed_materials(materials_dir: Path, project_name: str, project_description: str | None) -> None:
    with get_db() as db:
        project_repo = ProjectRepository(db)
        project = project_repo.get_project_by_name(project_name)
        if project is None:
            project = project_repo.create_project(project_name, project_description)

        document_repo = DocumentRepository(db)
        files = [
            path
            for path in sorted(materials_dir.rglob("*"))
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        ]
        if not files:
            print(f"No supported files found in {materials_dir}")
            return

        for path in files:
            existing = (
                db.query(models.Document)
                .filter(
                    models.Document.project_id == project.id,
                    models.Document.filename == path.name,
                )
                .first()
            )
            if existing:
                print(f"Skipping existing document: {path.name}")
                continue

            content_type = mimetypes.guess_type(path.name)[0] or "text/plain"
            document = document_repo.create_document(path.name, content_type, project.id)
            try:
                text = parse_file_bytes(path.read_bytes(), filename=path.name, content_type=content_type)
                chunks = split_text(text, chunk_size=512, overlap=50)
                for index, chunk in enumerate(chunks):
                    embedding = await get_embedding(chunk)
                    document_repo.add_chunk(document.id, index, chunk, embedding=embedding)
                document_repo.update_document_status(document.id, "processed")
                print(f"Loaded {path.name}: {len(chunks)} chunks")
            except Exception:
                document_repo.update_document_status(document.id, "failed")
                raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed local demo/reference materials into ArchPilot.")
    parser.add_argument("--materials-dir", default="data/samples/demo-materials")
    parser.add_argument("--project-name", default="ArchPilot Demo Reference")
    parser.add_argument("--project-description", default="Seeded local reference material for demo questions.")
    args = parser.parse_args()

    asyncio.run(
        seed_materials(
            materials_dir=Path(args.materials_dir),
            project_name=args.project_name,
            project_description=args.project_description,
        )
    )


if __name__ == "__main__":
    main()
