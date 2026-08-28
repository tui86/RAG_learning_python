from __future__ import annotations

import hashlib
import os
import pickle
import re
import math
from typing import List, Tuple

import chromadb
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder, SentenceTransformer

from .config import logger



class HybridRetriever:
    '''Lớp để quản lý việc truy xuất thông tin từ cơ sở dữ liệu vector, kết hợp giữa dense retrieval (Chroma DB) và sparse retrieval (BM25).'''
    def __init__(self, db_path: str, pickle_path: str | None = None):
        self.db_path = db_path
        self.pickle_path = pickle_path or os.path.join(db_path, "bm25_cache.pkl")
        self.model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        self.rerank = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        self.client = chromadb.PersistentClient(path=self.db_path)
        self.collection = self.client.get_or_create_collection(
            name="rag_knowledge_base",
            metadata={"hnsw:space": "cosine"},
        )
        self.bm25 = None
        self.all_ids: List[str] = []
        self.name_vector: List[str] = []

    @staticmethod
    def _generate_chunk_id(chunk_text: str) -> str:
        '''Tạo một ID duy nhất cho mỗi chunk dựa trên hash SHA-256 của nội dung chunk.'''
        return hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()

    def _load_cache(self) -> bool:
        '''Tải cache BM25 từ file pickle nếu tồn tại. Trả về True nếu tải thành công, False nếu không có cache.'''
        if not os.path.exists(self.pickle_path):
            return False
        with open(self.pickle_path, "rb") as handle:
            cache_data = pickle.load(handle)
        self.bm25 = cache_data.get("bm25")
        self.all_ids = cache_data.get("all_ids", [])
        self.name_vector = cache_data.get("name_vector", [])
        return self.bm25 is not None

    def _save_cache(self) -> None:
        '''Lưu cache BM25 vào file pickle để sử dụng lại sau này.'''
        os.makedirs(os.path.dirname(self.pickle_path), exist_ok=True)
        with open(self.pickle_path, "wb") as handle:
            pickle.dump(
                {
                    "bm25": self.bm25,
                    "all_ids": self.all_ids,
                    "name_vector": self.name_vector,
                },
                handle,
            )

    @staticmethod
    def __sigmoid(x: float) -> float [0.0, 1.0]:
        if x < -100:
            return 0.0
        if x > 100:
            return 1.0
        return 1/(1 + math.exp(-x))

    def build_index(self, chunks: List[str], sources: List[str]) -> None:
        '''Xây dựng chỉ mục vector từ các chunks và lưu vào Chroma DB, đồng thời cập nhật cache BM25.'''
        existing_ids = set(self.collection.get()["ids"]) if self.collection.count() > 0 else set()
        ids: List[str] = []
        unique_chunks: List[str] = []
        unique_sources: List[str] = []

        for chunk, source in zip(chunks, sources):
            chunk_id = self._generate_chunk_id(chunk)
            if chunk_id in existing_ids:
                continue
            existing_ids.add(chunk_id)
            unique_chunks.append(chunk)
            unique_sources.append(source)
            ids.append(chunk_id)

        if not ids:
            logger.info("Không có chunk mới để thêm vào kho vector")
            return

        embeddings = self.model.encode(unique_chunks)
        metadatas = [{"source": src, "chunk_id": idx + 1} for idx, src in enumerate(unique_sources)]
        self.collection.add(embeddings=embeddings, documents=unique_chunks, metadatas=metadatas, ids=ids)
        self.all_ids.extend(ids)
        self.name_vector.extend(unique_sources)

        tokenized_corpus = [re.findall(r"\w+", chunk.lower()) for chunk in unique_chunks]
        self.bm25 = BM25Okapi(tokenized_corpus) if self.bm25 is None else self.bm25
        self._save_cache()
        logger.info("Đã lưu trữ chunks vào Chroma DB")

    def load_index(self) -> None:
        '''Tải chỉ mục từ Chroma DB và cache BM25 nếu tồn tại.'''
        if self._load_cache() and self.collection.count() > 0:
            logger.info("Đã tải cache và index từ Chroma DB")
            return
        logger.info("Chưa có cache, sẽ tạo index khi dữ liệu được cung cấp")

    def retriever(self, question: str, top_k: int = 15, final_top_k: int = 10, k_min: int = 2, rrf_k: int = 60, score_percentile: float = 0.75) -> str:
        """
        Retriever sử dụng percentile-based selection để chọn chunks tốt nhất.
        
        Args:
            question: Câu hỏi cần trả lời
            top_k: Số lượng ứng viên tối đa để rerank
            final_top_k: Số lượng chunks tối đa để trả về
            k_min: Số lượng chunks tối thiểu để trả về
            rrf_k: Tham số RRF fusion
            score_percentile: Ngưỡng percentile (0-1) để giữ lại chunks. Default: 0.75 (giữ top 75%)
        """
        if self.collection.count() == 0:
            return ""

        # Lấy kết quả từ dense và sparse retrieval
        dense_query = self.model.encode([question]).tolist()
        dense_results = self.collection.query(query_embeddings=dense_query, n_results=top_k)
        dense_ids = dense_results["ids"][0]

        # Lấy kết quả từ sparse retrieval (BM25)
        tokenized_question = re.findall(r"\w+", question.lower())
        sparse_scores = self.bm25.get_scores(tokenized_question) if self.bm25 is not None else np.zeros(len(self.all_ids))
        sparse_indices = np.argsort(sparse_scores)[::-1][:top_k].tolist()
        sparse_ids = [self.all_ids[i] for i in sparse_indices if i < len(self.all_ids)]

        # Kết hợp kết quả dense và sparse retrieval bằng Reciprocal Rank Fusion (RRF)
        dense_rank = {idx: rank + 1 for rank, idx in enumerate(dense_ids)}
        sparse_rank = {idx: rank + 1 for rank, idx in enumerate(sparse_ids)}

        # Tính điểm RRF cho tất cả các ứng viên
        all_candidates = set(dense_rank.keys()).union(set(sparse_rank.keys()))
        score_rrf: dict[str, float] = {}
        for idx in all_candidates:
            score = 0.0
            if idx in dense_rank:
                score += 1 / (rrf_k + dense_rank[idx])
            if idx in sparse_rank:
                score += 1 / (rrf_k + sparse_rank[idx])
            score_rrf[idx] = score

        # Sắp xếp các ứng viên theo điểm RRF và lấy thông tin từ Chroma DB
        fused_ids = sorted(score_rrf.keys(), key=lambda item: score_rrf[item], reverse=True)
        db_records = self.collection.get(ids=fused_ids)
        candidate_chunks = db_records.get("documents", [])
        candidate_metadatas = db_records.get("metadatas", [])

        if not candidate_chunks:
            return ""

        # Rerank các ứng viên bằng CrossEncoder
        cross_inputs = [[question, chunk] for chunk in candidate_chunks]
        cross_scores = self.rerank.predict(cross_inputs)
        cross_result = [self.__sigmoid(score) for score in cross_scores]
        scored_results = sorted(
            zip(cross_result, candidate_chunks, candidate_metadatas),
            key=lambda item: item[0],
            reverse=True,
        )

        # Lọc các chunks dựa trên percentile-based selection
        logger.info("Scored results: %s", scored_results)
        top_best_score = scored_results[0][0]
        percentile_threshold = top_best_score * score_percentile
        
        best_chunks = []
        for i, (score, chunk, metadata) in enumerate(scored_results):
            if i < k_min:
                best_chunks.append(scored_results[i])
                continue

            if i >= final_top_k:
                break
            
            if score >= percentile_threshold:
                best_chunks.append(scored_results[i])
            else:
                break

        formatted_context = []
        for score, chunk_text, meta in best_chunks:
            source = meta.get("source", "Unknown")
            formatted_context.append(f"[Nguồn: {source}]\n{chunk_text}")
        return "\n\n---\n\n".join(formatted_context)
