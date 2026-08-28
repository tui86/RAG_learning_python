from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from .config import logger
from .document_loader import ReadData
from .generator import QueryGenerator
from .retriever import HybridRetriever
from .text_splitter import TextSplitter
from .graphRAG import GraphRAGManager

GLOBAL_KEYWORDS = ["tóm tắt", "chủ đề chính", "tổng quan", "toàn bộ", "xuyên suốt", "cấu trúc cuốn sách"]

class RAG_System:
    '''Lớp quản lý toàn bộ hệ thống RAG (Retrieval-Augmented Generation), bao gồm việc nạp tài liệu, truy vấn và quản lý đồ thị tri thức.'''
    def __init__(self, data_dir: str = "data", db_path: str | None = None):
        self.data_dir = Path(data_dir)
        self.db_path = Path(db_path or self.data_dir / "rag_vector_db")
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.retriever = HybridRetriever(str(self.db_path), str(self.data_dir / "bm25_cache.pkl"))
        self.generator = QueryGenerator()
        self.text_splitter = TextSplitter()
        self.loader = ReadData(str(self.data_dir / "papers"))
        self.graphRAG = GraphRAGManager(pickle_graph_path=str(self.data_dir/"graph_cache.pkl"))

    def ingest_documents(self, folder_path: str | None = None, create_knowledge_graph: bool = False) -> None:
        '''Thêm tài liệu vào hệ thống RAG, bao gồm đọc PDF, tách văn bản, xây dựng chỉ mục và (tùy chọn) xây dựng đồ thị tri thức.'''
        loader = self.loader if folder_path is None else ReadData(folder_path)
        texts, names = loader.read_pdf()
        chunks, sources = self.text_splitter.split_texts(texts, names)
        self.retriever.build_index(chunks, sources)
        if create_knowledge_graph: self.graphRAG.build_knowledge_graph(chunks)
        logger.info("Đã ingest tài liệu vào hệ thống RAG")

    def query(self, question: str, mode: str = 'local') -> dict:
        '''Xử lý câu hỏi từ người dùng, xác định chế độ (toàn cục hoặc cục bộ), và trả về câu trả lời cùng với ngữ cảnh.'''
        if mode == 'global':
            standalone_query = self.generator._get_standalone_query(question)
            answer, context = self.graphRAG.global_search_answer(question=standalone_query)
        elif mode == 'local':
            standalone_query = self.generator._get_standalone_query(question)
            context = self.retriever.retriever(standalone_query)
            answer = self.generator.generate_answer(question, context)
        else:
            raise ValueError("mode không tồn tại")
        return {"answer": answer, "documents": [context]}

    def run_terminal(self) -> None:
        '''Chạy hệ thống RAG trong chế độ terminal, cho phép người dùng nhập câu hỏi và nhận câu trả lời.'''
        self.retriever.load_index()
        while True:
            user_question = input("Nhập câu hỏi của bạn (hoặc 'exit' để thoát): ")
            if user_question.lower() == "exit":
                break
            result = self.query(user_question)
            print(f"Câu trả lời: {result['answer']}")
