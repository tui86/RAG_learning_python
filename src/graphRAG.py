import os
import re
import json
import pickle
import hashlib
import networkx as nx
import ollama
import atexit
import tqdm
from pathlib import Path
from .generator import QueryGenerator
from src.config import get_env, logger
from neo4j import GraphDatabase
from gliner import GLiNER

class GraphRAGManager:
    '''Lớp quản lý đồ thị tri thức cho các tác vụ RAG (Retrieval-Augmented Generation).'''
    def __init__(self, auth:tuple = None, neo4j_uri: str = 'http://localhost:7474', pickle_graph_path: str = None):
        self.graph = nx.Graph()
        self.community_summaries = []
        self.generator = QueryGenerator()
        self.uri = get_env(name='NEO4J_URI') or neo4j_uri
        self.auth = (get_env("NEO4J_USERNAME"), get_env("NEO4J_PASSWORD")) or auth
        self.driver = GraphDatabase.driver(self.uri, auth=self.auth)
        self.gliner = GLiNER.from_pretrained("urchade/gliner_base")
        self.pickle_graph_path = pickle_graph_path or os.path.join(os.getcwd(), "data", "knowledge_graph.pkl")
        self.driver.verify_connectivity()
        self._register_shutdown()
        self._create_constraint()

    def _create_constraint(self):
        # Tạo các ràng buộc duy nhất cho các nút trong Neo4j để đảm bảo tính toàn vẹn dữ liệu.
        with self.driver.session() as session:
            for label, property_name in (
                ("Book", "book_id"),
                ("Section", "section_id"),
                ("Chunk", "chunk_id"),
                ("Summary", "summary_id"),
                ("Entity", "entity_id"),
                ("Claim", "claim_id"),
                ("Evidence", "evidence_id"),
            ):
                session.run(
                    f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.{property_name} IS UNIQUE"
                )
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE")

    @staticmethod
    def _stable_id(*parts: str) -> str:
        return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()

    @staticmethod
    def _create_elements(tx, graph_data):
        ''' Tạo các nút và quan hệ trong Neo4j dựa trên dữ liệu đồ thị tri thức đã được chuẩn bị.'''

        # Tạo các nút Book
        tx.run('''
            UNWIND $rows AS row
            MERGE (book:Book {book_id: row.book_id})
            SET book.title = row.title, book.file_hash = row.file_hash
        ''', rows=graph_data["books"])

        # Tạo các nút Section và quan hệ HAS_SECTION với Book
        tx.run('''
            UNWIND $rows AS row
            MERGE (section:Section {section_id: row.section_id})
            SET section.title = row.title, section.level = row.level,
                section.start_page = row.start_page, section.end_page = row.end_page,
                section.path = row.path
            WITH section, row
            MATCH (book:Book {book_id: row.book_id})
            MERGE (book)-[:HAS_SECTION]->(section)
        ''', rows=graph_data["sections"])

        # Tạo các quan hệ PARENT_OF giữa các Section
        tx.run('''
            UNWIND $rows AS row
            MATCH (parent:Section {section_id: row.parent_id})
            MATCH (child:Section {section_id: row.child_id})
            MERGE (parent)-[:PARENT_OF]->(child)
        ''', rows=graph_data["parent_edges"])

        # Tạo các nút Chunk và quan hệ HAS_CHUNK với Section
        tx.run('''
            UNWIND $rows AS row
            MERGE (chunk:Chunk {chunk_id: row.chunk_id})
            SET chunk.text = row.text, chunk.start_page = row.start_page,
                chunk.end_page = row.end_page
            WITH chunk, row
            MATCH (section:Section {section_id: row.section_id})
            MERGE (section)-[:HAS_CHUNK]->(chunk)
        ''', rows=graph_data["chunks"])

        # Tạo các nút Entity và quan hệ MENTIONS giữa Chunk và Entity
        tx.run('''
            UNWIND $rows AS row
            MERGE (entity:Entity {entity_id: row.entity_id})
            SET entity.name = row.name, entity.type = row.type, entity.aliases = row.aliases
        ''', rows=graph_data["entities"])

        # Tạo các quan hệ MENTIONS giữa Chunk và Entity
        tx.run('''
            UNWIND $rows AS row
            MATCH (chunk:Chunk {chunk_id: row.chunk_id})
            MATCH (entity:Entity {entity_id: row.entity_id})
            MERGE (chunk)-[:MENTIONS]->(entity)
        ''', rows=graph_data["mentions"])

        # Tạo các quan hệ RELATED_TO giữa các Entity
        tx.run('''
            UNWIND $rows AS row
            MERGE (claim:Claim {claim_id: row.claim_id})
            SET claim.statement = row.statement, claim.confidence = row.confidence,
                claim.relation = row.relation,
                claim.source_entity_id = row.source_entity_id,
                claim.target_entity_id = row.target_entity_id
        ''', rows=graph_data["claims"])

        # Tạo các nút Evidence và quan hệ SUPPORTED_BY giữa Claim và Evidence
        tx.run('''
            UNWIND $rows AS row
            MERGE (evidence:Evidence {evidence_id: row.evidence_id})
            SET evidence.quote = row.quote, evidence.page = row.page,
                evidence.chunk_id = row.chunk_id
        ''', rows=graph_data["evidence"])

        # Tạo các quan hệ SUPPORTED_BY giữa Claim và Evidence
        tx.run('''
            UNWIND $rows AS row
            MATCH (claim:Claim {claim_id: row.claim_id})
            MATCH (evidence:Evidence {evidence_id: row.evidence_id})
            MERGE (claim)-[:SUPPORTED_BY]->(evidence)
        ''', rows=graph_data["supported_by"])

        # Tạo các quan hệ RELATED_TO giữa các Entity
        tx.run('''
            UNWIND $rows AS row
            MATCH (source:Entity {entity_id: row.source_id})
            MATCH (target:Entity {entity_id: row.target_id})
            MERGE (source)-[relation:RELATED_TO {name: row.relation}]->(target)
            SET relation.description = row.relation
        ''', rows=graph_data["relations"])

        # Tạo các quan hệ NEXT_SECTION giữa các Section
        tx.run('''
            UNWIND $rows AS row
            MATCH (section:Section {section_id: row.section_id})
            MATCH (next:Section {section_id: row.next_section_id})
            MERGE (section)-[:NEXT_SECTION]->(next)
        ''', rows=graph_data["next_edges"])

    @staticmethod
    def _create_section_summary(tx, section_id, summary):
        '''Tạo nút Summary và quan hệ HAS_SUMMARY giữa Section và Summary.'''
        tx.run('''
            MATCH (section:Section {section_id: $section_id})
            MERGE (summary:Summary {summary_id: $summary.summary_id})
            SET summary.text = $summary.text, summary.model_version = $summary.model_version
            MERGE (section)-[:HAS_SUMMARY]->(summary)
        ''', section_id=section_id, summary=summary)

    @staticmethod
    def _create_legacy_elements(tx, batch_edges):
        '''Tạo các nút Entity và quan hệ RELATED_TO giữa các Entity từ dữ liệu legacy.'''
        tx.run('''
            UNWIND $batch AS row
            MERGE (source:Entity {name: row.source})
            MERGE (target:Entity {name: row.target})
            MERGE (source)-[relation:RELATED_TO {name: row.relation}]->(target)
            SET relation.description = row.relation
        ''', batch=batch_edges)

    @staticmethod
    def _create_legacy_summary(tx, summary):
        '''Tạo các nút Summary và quan hệ HAS_SUMMARY giữa Entity và Summary từ dữ liệu legacy.'''
        tx.run('''
            UNWIND $rows AS row
            MATCH (entity:Entity {name: row.entity})
            MERGE (summary:Summary {summary_id: row.summary_id})
            SET summary.text = row.text, summary.model_version = row.model_version
            MERGE (entity)-[:HAS_SUMMARY]->(summary)
        ''', rows=summary)


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

        batch_size = 30
        with self.driver.session() as session:
            for start in tqdm.tqdm(range(0, len(edges_data), batch_size), desc="Đang Ingest vào Neo4j"):
                batch = edges_data[start : start + batch_size]
                session.execute_write(self._create_legacy_elements, batch)
            legacy_summaries = []
            for index, summary_text in enumerate(self.community_summaries):
                for entity in {edge[key] for edge in edges_data for key in ("source", "target")}:
                    legacy_summaries.append({
                        "entity": entity,
                        "summary_id": self._stable_id(str(index), entity),
                        "text": summary_text,
                        "model_version": "legacy",
                    })
            if legacy_summaries:
                session.execute_write(self._create_legacy_summary, legacy_summaries)
        print(f"Đã ingest {len(edges_data)} edges và {len(self.community_summaries)} summaries vào Neo4j.")

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
                    OPTIONAL MATCH (summary_section:Section)-[:PARENT_OF*0..]->(:Section)
                        -[:HAS_CHUNK]->(:Chunk)-[:MENTIONS]->(e)
                    OPTIONAL MATCH (summary_section)-[:HAS_SUMMARY]->(s:Summary)
                    OPTIONAL MATCH (e)-[:HAS_SUMMARY]->(legacy_summary:Summary)
                    RETURN e.name AS name_entity, 
                    collect(DISTINCT s.text) + collect(DISTINCT legacy_summary.text) AS Summary,
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

    def build_knowledge_graph(self, chunks: list[str | dict], sources: list[str]):
        """Xây dựng đồ thị tri thức từ các chunks và lưu vào Neo4j.
           chunks: list[str | dict] - Danh sách các chunks văn bản hoặc dict chứa thông tin chunk.
           return: None
        """
        if not chunks:
            logger.warning("Không có chunks để xây dựng đồ thị tri thức.")
            return

        if sources and len(sources) != len(chunks):
            raise ValueError("sources phải có cùng số phần tử với chunks")
        resolved_sources = sources or ["unknown"] * len(chunks)
        graph_data = {
            "books": {}, "sections": {}, "chunks": [], "entities": {},
            "mentions": set(), "relations": {}, "claims": {}, "evidence": {},
            "supported_by": set(), "parent_edges": set(), "next_edges": set(),
        }
        book_contents = {}
        book_section_order = {}
        summary_sections = {}

        for index, (chunk, source_name) in enumerate(zip(chunks, resolved_sources)):
            if isinstance(chunk, str):
                chunk_text, metadata = chunk, {}
            elif hasattr(chunk, "page_content"):
                chunk_text, metadata = chunk.page_content, chunk.metadata
            elif isinstance(chunk, dict):
                chunk_text, metadata = chunk.get("text", ""), chunk.get("metadata", {})
            else:
                raise TypeError(f"Kiểu chunk không được hỗ trợ: {type(chunk).__name__}")
            if not chunk_text.strip():
                continue

            source_name = str(source_name)
            title = Path(source_name).stem or source_name
            book_id = self._stable_id(source_name.casefold())
            book_contents.setdefault(book_id, []).append(chunk_text)
            book_section_order.setdefault(book_id, [])

            header_titles = []
            for level in range(1, 4):
                header_title = metadata.get(f"Header {level}")
                if header_title:
                    header_titles.append((level, str(header_title).strip()))
            if not header_titles:
                header_titles = [(0, title)]

            parent_id = None
            path_parts = []
            for level, section_title in header_titles:
                path_parts.append(section_title)
                section_path = " > ".join(path_parts)
                section_id = self._stable_id(book_id, section_path)
                graph_data["sections"].setdefault(section_id, {
                    "section_id": section_id,
                    "book_id": book_id,
                    "title": section_title,
                    "level": level,
                    "start_page": None,
                    "end_page": None,
                    "path": section_path,
                })
                if parent_id:
                    graph_data["parent_edges"].add((parent_id, section_id))
                parent_id = section_id
                if section_id not in book_section_order[book_id]:
                    book_section_order[book_id].append(section_id)
                if level == 2:
                    summary_sections[section_id] = section_title

            section_id = parent_id
            chunk_id = self._stable_id(book_id, str(index), chunk_text)
            graph_data["chunks"].append({
                "chunk_id": chunk_id,
                "section_id": section_id,
                "text": chunk_text,
                "start_page": metadata.get("start_page"),
                "end_page": metadata.get("end_page"),
            })

            triplets = self.generator.extract_triplets_from_chunk(chunk_text)
            for triplet in triplets:
                source_entity = str(triplet.get("source", "")).strip()
                target_entity = str(triplet.get("target", "")).strip()
                relation = str(triplet.get("relation", "")).strip()
                if not source_entity or not target_entity or not relation:
                    continue
                entity_ids = []
                for name in (source_entity, target_entity):
                    entity_id = self._stable_id(name.casefold())
                    graph_data["entities"].setdefault(entity_id, {
                        "entity_id": entity_id,
                        "name": name,
                        "type": "concept",
                        "aliases": [],
                    })
                    graph_data["mentions"].add((chunk_id, entity_id))
                    entity_ids.append(entity_id)
                graph_data["relations"][(entity_ids[0], relation, entity_ids[1])] = {
                    "source_id": entity_ids[0],
                    "target_id": entity_ids[1],
                    "relation": relation,
                }
                claim_id = self._stable_id(chunk_id, source_entity, relation, target_entity)
                evidence_id = self._stable_id(chunk_id, "evidence")
                graph_data["claims"][claim_id] = {
                    "claim_id": claim_id,
                    "statement": f"{source_entity} {relation} {target_entity}",
                    "confidence": None,
                    "relation": relation,
                    "source_entity_id": entity_ids[0],
                    "target_entity_id": entity_ids[1],
                }
                graph_data["evidence"][evidence_id] = {
                    "evidence_id": evidence_id,
                    "quote": chunk_text,
                    "page": metadata.get("start_page"),
                    "chunk_id": chunk_id,
                }
                graph_data["supported_by"].add((claim_id, evidence_id))

        for book_id, content_parts in book_contents.items():
            source_name = next(
                str(source) for source in resolved_sources
                if self._stable_id(str(source).casefold()) == book_id
            )
            graph_data["books"][book_id] = {
                "book_id": book_id,
                "title": Path(source_name).stem or source_name,
                "file_hash": hashlib.sha256("\n".join(content_parts).encode("utf-8")).hexdigest(),
            }
            ordered_sections = book_section_order[book_id]
            graph_data["next_edges"].update(zip(ordered_sections, ordered_sections[1:]))

        graph_data["books"] = list(graph_data["books"].values())
        graph_data["sections"] = list(graph_data["sections"].values())
        graph_data["entities"] = list(graph_data["entities"].values())
        graph_data["mentions"] = [
            {"chunk_id": chunk_id, "entity_id": entity_id}
            for chunk_id, entity_id in graph_data["mentions"]
        ]
        graph_data["relations"] = list(graph_data["relations"].values())
        graph_data["claims"] = list(graph_data["claims"].values())
        graph_data["evidence"] = list(graph_data["evidence"].values())
        graph_data["supported_by"] = [
            {"claim_id": claim_id, "evidence_id": evidence_id}
            for claim_id, evidence_id in graph_data["supported_by"]
        ]
        graph_data["parent_edges"] = [
            {"parent_id": parent_id, "child_id": child_id}
            for parent_id, child_id in graph_data["parent_edges"]
        ]
        graph_data["next_edges"] = [
            {"section_id": section_id, "next_section_id": next_section_id}
            for section_id, next_section_id in graph_data["next_edges"]
        ]
        if not graph_data["books"]:
            return

        with self.driver.session() as session:
            session.execute_write(self._create_elements, graph_data)

        logger.info("Đã ghi Book, Section, Chunk, Entity và các quan hệ vào Neo4j.")
        for section_id, section_title in tqdm.tqdm(summary_sections.items(), desc="Tạo tóm tắt Section cấp 2"):
            with self.driver.session() as session:
                record = session.run('''
                    MATCH (section:Section {section_id: $section_id})
                    OPTIONAL MATCH (section)-[:PARENT_OF*0..]->(:Section)-[:HAS_CHUNK]->(chunk:Chunk)
                    WITH section, collect(DISTINCT chunk.text) AS chunk_texts,
                         collect(DISTINCT chunk) AS chunks
                    UNWIND CASE WHEN size(chunks) = 0 THEN [null] ELSE chunks END AS chunk
                    OPTIONAL MATCH (chunk)-[:MENTIONS]->(entity:Entity)-[relation:RELATED_TO]-(related:Entity)
                    RETURN section.title AS title, chunk_texts,
                           collect(DISTINCT CASE WHEN relation IS NULL THEN null
                             ELSE entity.name + " -" + relation.description + "-> " + related.name END) AS relations
                ''', section_id=section_id).single()

            if not record:
                continue
            section_texts = record.get("chunk_texts") or []
            section_relations = record.get("relations") or []
            summary_input = "\n\n".join(
                [f"Section: {section_title}"] + section_texts + section_relations
            )
            summary_text = self.generator.summary_nodes(edges_text=summary_input)
            summary = {
                "summary_id": self._stable_id(section_id, "summary"),
                "text": summary_text,
                "model_version": "qwen2.5",
            }
            with self.driver.session() as session:
                session.execute_write(self._create_section_summary, section_id, summary)

        logger.info("Đã tạo và gắn summary vào từng Section cấp 2.")

    
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

    