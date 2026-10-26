from pathlib import Path

from src.rag_pipeline import RAG_System


def build() -> None:
    project_root = Path(__file__).resolve().parent
    rag_build = RAG_System(data_dir=str(project_root / "data"))
    rag_build.ingest_documents(create_knowledge_graph=True)

if __name__ == "__main__":
    build()
