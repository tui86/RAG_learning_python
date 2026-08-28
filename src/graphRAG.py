import os
import re
import json
import pickle
import networkx as nx
import ollama
from .generator import QueryGenerator
from .config import logger

class GraphRAGManager:
    '''Lớp quản lý đồ thị tri thức cho các tác vụ RAG (Retrieval-Augmented Generation).'''
    def __init__(self, pickle_graph_path = './graph_cache.pkl'):
        self.pickle_graph_path = pickle_graph_path
        self.graph = nx.Graph()
        self.community_summaries = []
        self.generator = QueryGenerator()

    def _read_graph(self, pickle_file: str) -> None:
        '''Đọc đồ thị tri thức và các tóm tắt cộng đồng từ file pickle.'''
        with open(pickle_file, "rb") as f:
            data = pickle.load(f)
            self.graph = data["graph"]
            self.community_summaries = data["community_summaries"]
        return

    def _write_graph(self, pickle_file: str) -> None:
        '''Ghi đồ thị tri thức và các tóm tắt cộng đồng vào file pickle.'''
        with open(pickle_file, 'wb') as f:
            pickle.dump({
                "graph": self.graph,
                "community_summaries": self.community_summaries
            }, f)
        return

    def is_graph_built(self) -> bool:
        '''Kiểm tra xem đồ thị tri thức đã được xây dựng và lưu vào cache hay chưa.'''
        return os.path.exists(self.pickle_graph_path)


    def build_knowledge_graph(self, chunks: list[dict]):
        '''Xây dựng đồ thị tri thức từ các chunks và lưu vào cache.'''
        if not chunks:
            logger.warning("Không có chunks để xây dựng đồ thị tri thức.")
            return
        if self.is_graph_built():
            self._read_graph(self.pickle_graph_path)
            return

        for chunk in chunks:
            chunk_text = chunk if isinstance(chunk, str) else chunk.get("text", "")
            triplets = self.generator.extract_triplets_from_chunk(chunk_text)
            for t in triplets:
                src = t.get('source')
                rel = t.get('relation')
                tgt = t.get('target')
                if src and rel and tgt:
                    self.graph.add_node(src)
                    self.graph.add_node(tgt)
                    self.graph.add_edge(src, tgt, relation=rel)
            

        communities = list(nx.connected_components(self.graph))

        summaries = []

        for i, com in enumerate(communities):
            if len(com) < 2:
                continue
            subgraph = self.graph.subgraph(com)
            edge_info = []
            for u, v, r in subgraph.edges(data=True):
                edge_info.append(f"- {u} --[{r.get('relation', 'RELATED')}]--> {v}")

            edges_text = '\n'.join(edge_info[:30])
            summary = self.generator.summary_nodes(edges_text=edges_text)
            summaries.append(f"### Cụm Tri Thức {i+1}:\n{summary}")

        self.community_summaries = summaries
        self._write_graph(self.pickle_graph_path)
        logger.info("Đã xây dựng Đồ thị tri thức và lưu vào cache.")

    def global_search_answer(self, question: str) -> tuple[str, str]:
        """Trả lời các câu hỏi tóm tắt toàn bộ tài liệu dựa trên các Community Summaries."""
        self._read_graph(self.pickle_graph_path)
        if not self.community_summaries:
            return "Chưa có dữ liệu Đồ thị tri thức.", ""

        all_summaries_text = "\n\n".join(self.community_summaries)

        response = self.generator.graph_search_answer(question=question, summaries_text=all_summaries_text)

        return response, all_summaries_text
