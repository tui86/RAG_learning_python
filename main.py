from pathlib import Path

from src.rag_pipeline import RAG_System


def main() -> None:
    project_root = Path(__file__).resolve().parent
    rag = RAG_System(data_dir=str(project_root / "data"))
    rag.run_terminal()


if __name__ == "__main__":
    main()
