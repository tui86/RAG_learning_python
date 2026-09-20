import os
import re
import json
import pickle
import networkx as nx
import ollama
import atexit
import tqdm
from .generator import QueryGenerator
from src.config import get_env, logger
from neo4j import GraphDatabase
from gliner import GLiNER

class GraphRAGManager:
    '''Lớp quản lý đồ thị tri thức cho các tác vụ RAG (Retrieval-Augmented Generation).'''
    def __init__(self, auth:tuple = None, neo4j_uri: str = 'http://localhost:7474'):
        self.graph = nx.Graph()
        self.community_summaries = []
        self.generator = QueryGenerator()
        self.uri = get_env(name='NEO4J_URI') or neo4j_uri
        self.auth = (get_env("NEO4J_USERNAME"), get_env("NEO4J_PASSWORD")) or auth
        self.driver = GraphDatabase.driver(self.uri, auth=self.auth)
        self.gliner = GLiNER.from_pretrained("urchade/gliner_base")
        self.driver.verify_connectivity()
        self._register_shutdown()
        self._create_constraint()

    def _create_constraint(self):
        with self.driver.session() as session:
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE")

    def _create_elements_and_summary(self, tx, batch_edges, summary):
        query = ''' UNWIND $batch AS row
        MERGE (source:Entity {name: row.source})
        MERGE (target:Entity {name: row.target})
        MERGE (source)-[r:RELATED_TO]->(target)
        SET r.description = row.relation
        MERGE (s:summary {summary_id: $summary.id})
        SET s.summary_text = $summary.summary
        MERGE (source)-[:HAS_SUMMARY]->(s)
        MERGE (target)-[:HAS_SUMMARY]->(s)'''
        tx.run(query, batch=batch_edges, summary=summary)


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

    def convert_pkl_to_neo(self):
        """Chuyển đổi file pkl sang neo4j"""
        self._read_graph(self.pickle_graph_path)
        edges_data = []
        for u, v, data in self.graph.edges(data=True):
            edges_data.append({
                "source": str(u).strip(),
                "target": str(v).strip(),
                "relation": str(data.get("relation", "RELATED_TO")).strip()
            })

        BATCH_SIZE = 30
        count_summary = 0
        with self.driver.session() as session:
            for i in tqdm.tqdm(range(0, len(edges_data), BATCH_SIZE), desc="Đang Ingest vào Neo4j"):
                batch = edges_data[i : i + BATCH_SIZE]
                summary = {'summary':self.community_summaries[count_summary] if count_summary < len(self.community_summaries) else "No summary available", 
                           'id':count_summary}
                session.execute_write(self._create_elements_and_summary, batch, summary)
                count_summary += 1
        print(f"Đã ingest {len(edges_data)} edges và {count_summary} summaries vào Neo4j.")

    def _normalize_text(self, extracted_entities: list[str]) -> list[str]:
        """Chuẩn hóa thực thể văn bản theo dữ liệu trong Neo4j."""
        query = """CALL db.index.fulltext.queryNodes("entity_name_index", $keyword)
            YIELD node, score WHERE score > 0.5
            RETURN node.name AS name_entity"""
        normalized_entities = []
        with self.driver.session() as session:
            for entity in extracted_entities:
                clean_entity = re.sub(r"[^\w\s]", " ", entity, flags=re.UNICODE)
                clean_entity = re.sub(r"\s+", " ", clean_entity).strip()
                fuzzy_keyword = f"{clean_entity}~"
                result = session.run(query, keyword=fuzzy_keyword)
                for record in result:
                    normalized_entities.append(record['name_entity'])
        return list(dict.fromkeys(normalized_entities))


    def get_context_from_neo4j(self, extracted_entities: list[str]) -> str:
        """Truy vấn Neo4j để lấy ngữ cảnh dựa trên các thực thể đã trích xuất."""
        normalized_entities = self._normalize_text(extracted_entities)
        
        query = """MATCH (e:Entity) WHERE toLower(e.name) IN [x IN $entity_list | toLower(x)]
                    OPTIONAL MATCH (e)-[r:RELATED_TO]->(n:Entity)
                    OPTIONAL MATCH (e)-[h:HAS_SUMMARY]->(s:summary)
                    RETURN e.name AS name_entity, 
                    collect(DISTINCT s.summary_text) AS Summary,
                    collect(DISTINCT {rel: r.description, target: n.name}) AS details"""

        with self.driver.session() as session:
            result = session.run(query, entity_list = normalized_entities)

            context_blocks = []
            for record in result:
                name_entity = record['name_entity']
                summary = record['Summary']
                details = record['details']
                block = f"--- THÔNG TIN VỀ: {name_entity.upper()} ---\n"
                if summary and summary[0] is not None:
                    block += "Bức tranh toàn cảnh: "+"\n-".join(summary)+"\n\n"
                if details and details[0]['target'] is not None:
                    block += f"[Chi tiết liên kết]:\n"
                    for d in details[:10]: 
                        block += f"- {name_entity} {d['rel']} {d['target']}\n"
                context_blocks.append(block)
        return "\n\n".join(context_blocks)

    def generator_extracted_entities(self, question: str):
        '''Trích xuất các thực thể từ câu hỏi của người dùng.
           Sử dụng mô hình GLiNER để nhận diện các thực thể trong câu hỏi.
           question: str - Câu hỏi của người dùng.
           return: list[str] - Danh sách các thực thể đã trích xuất.'''
        labels = [
    "concept",
    "mathematical object",
    "matrix",
    "algorithm",
    "method",
    "model",
    "dataset",
    "software",
    "metric",
    "application",
    "research paper",
    "organization",
    "person",
    ]
        entity = self.gliner.predict_entities(question, labels=labels)
        return list(set([e["text"].lower() for e in entity]))

    def build_knowledge_graph(self, chunks: list[str | dict]):
        """Xây dựng đồ thị tri thức từ các chunks và lưu vào Neo4j.
           chunks: list[str | dict] - Danh sách các chunks văn bản hoặc dict chứa thông tin chunk.
           return: None
        """
        if not chunks:
            logger.warning("Không có chunks để xây dựng đồ thị tri thức.")
            return

        srcs, tgts, rels = [], [], []

        for chunk in chunks:
            chunk_text = chunk if isinstance(chunk, str) else chunk.get("text", "")
            triplets = self.generator.extract_triplets_from_chunk(chunk_text)
            with self.driver.session() as session:
                for t in triplets:
                    src = t.get('source')
                    rel = t.get('relation')
                    tgt = t.get('target')
                    if src and rel and tgt:
                        srcs.append(src)
                        tgts.append(tgt)
                        rels.append(rel)
        
        logger.info("Đã xây dựng Đồ thị tri thức từ các chunks và chuẩn bị lưu vào Neo4j.")

        edges_info = [f"- {u} --[{r}]--> {v}" for u, v, r in zip(srcs, tgts, rels)]
        summaries = []
        BATCH_SIZE = 30

        for i in tqdm.tqdm(range(0, len(edges_info), BATCH_SIZE), desc="Tạo tóm tắt cộng đồng"):
            batch_edges = edges_info[i : i + BATCH_SIZE]
            edges_text = '\n'.join(batch_edges)
            summary = self.generator.summary_nodes(edges_text=edges_text)
            summaries.append(f"### Cụm Tri Thức {i+1}:\n{summary}")
            with self.driver.session() as session:
                batch_data = [{"source": srcs[j], "relation": rels[j], "target": tgts[j]} for j in range(i, min(i + BATCH_SIZE, len(srcs)))]
                summary_data = {'summary': summary, 'id': i // BATCH_SIZE}
                session.execute_write(self._create_elements_and_summary, batch_data, summary_data)

        logger.info("Đã tạo tóm tắt cộng đồng và lưu vào Neo4j.")

    
    def global_search_answer(self, question: str) -> tuple[str, str]:
        """Trả lời các câu hỏi tóm tắt toàn bộ tài liệu dựa trên các Community Summaries.
           question: str - Câu hỏi của người dùng.
           return: tuple[str, str] - Câu trả lời và ngữ cảnh liên quan."""
        extracted_entities = self.generator_extracted_entities(question)
        context = self.get_context_from_neo4j(extracted_entities)
        answer = self.generator.generate_answer(question, context)
        return answer, context  
    
    def _register_shutdown(self):
        """Đăng ký cleanup tự động khi chương trình kết thúc."""
        try:
            atexit.register(self.close)
        except Exception:
            logger.warning("Không thể đăng ký shutdown hook cho Neo4j driver.")

    def close(self):
        """Đóng kết nối Neo4j nếu driver đang được khởi tạo."""
        try:
            if hasattr(self, 'driver') and self.driver is not None:
                self.driver.close()
                logger.info("Đã đóng kết nối Neo4j.")
        except Exception:
            logger.exception("Không thể đóng kết nối Neo4j.")

    def __del__(self):
        """Dọn dẹp dự phòng khi object bị hủy trước khi shutdown hook chạy."""
        try:
            self.close()
        except Exception:
            pass

    