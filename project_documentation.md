# Tên dự án: rag_project 

            Mô tả dự án: None 

            Các file trong dự án: ['rag_project/build.py', 'rag_project/main.py', 'rag_project/rag_web.py', 'rag_project/database/chat_history.py', 'rag_project/src/config.py', 'rag_project/src/document_loader.py', 'rag_project/src/generator.py', 'rag_project/src/graphRAG.py', 'rag_project/src/rag_pipeline.py', 'rag_project/src/retriever.py', 'rag_project/src/text_splitter.py', 'rag_project/src/__init__.py', 'rag_project/tests/query_data_test.py', 'rag_project/tests/test_env.py', 'rag_project/tests/test_graph_rag.py', 'rag_project/tests/translate.py', 'rag_project/web/UI.py'] 

            Chỉ đọc: False 
## Tên file: rag_project/build.py 

            Mô tả file: None 

            Các class trong file: [] 

            Các hàm lẻ trong file: ['build'] 

            Chỉ đọc: False 
#### Tên hàm: build 

                Decorator: [] 

                Mô tả hàm: None 

                Chỉ đọc: False 
## Tên file: rag_project/main.py 

            Mô tả file: None 

            Các class trong file: [] 

            Các hàm lẻ trong file: ['main'] 

            Chỉ đọc: False 
#### Tên hàm: main 

                Decorator: [] 

                Mô tả hàm: None 

                Chỉ đọc: False 
## Tên file: rag_project/rag_web.py 

            Mô tả file: None 

            Các class trong file: [] 

            Các hàm lẻ trong file: [] 

            Chỉ đọc: False 
## Tên file: rag_project/database/chat_history.py 

            Mô tả file: None 

            Các class trong file: ['ChatHistory'] 

            Các hàm lẻ trong file: [] 

            Chỉ đọc: False 
### Tên Lớp: ChatHistory 

            Mô tả lớp: Lớp quản lí dữ liệu từ MongoDB. 

            Các lớp được lớp này thừa kế: [] 

            Các hàm trong lớp này: ['__init__', 'create_new_session', 'add_message', 'get_chat_history', 'get_all_sessions'] 

            Chỉ đọc: False 
#### Tên hàm: __init__ 

                Decorator: [] 

                Mô tả hàm: None 

                Chỉ đọc: False 
#### Tên hàm: create_new_session 

                Decorator: [] 

                Mô tả hàm: Tạo một phiên chat (session) mới và trả về session_id. 

                Chỉ đọc: False 
#### Tên hàm: add_message 

                Decorator: [] 

                Mô tả hàm: Thêm một tin nhắn (của 'user' hoặc 'model') vào một phiên chat đã tồn tại.
Sử dụng toán tử $push của MongoDB để chỉ cập nhật mảng 'messages', không ghi đè toàn bộ document. 

                Chỉ đọc: False 
#### Tên hàm: get_chat_history 

                Decorator: [] 

                Mô tả hàm: Truy xuất lịch sử chat của một phiên (session_id).
Trả về `limit` tin nhắn gần nhất để nạp vào Context Window của LLM. 

                Chỉ đọc: False 
#### Tên hàm: get_all_sessions 

                Decorator: [] 

                Mô tả hàm: Lấy danh sách các phiên chat của một user để hiển thị trên UI (như sidebar của ChatGPT) 

                Chỉ đọc: False 
## Tên file: rag_project/src/config.py 

            Mô tả file: None 

            Các class trong file: [] 

            Các hàm lẻ trong file: ['configure_logging', 'get_env'] 

            Chỉ đọc: False 
#### Tên hàm: configure_logging 

                Decorator: [] 

                Mô tả hàm: Configure logging for the application. 

                Chỉ đọc: False 
#### Tên hàm: get_env 

                Decorator: [] 

                Mô tả hàm: Get an environment variable value, returning a default if not found. 

                Chỉ đọc: False 
## Tên file: rag_project/src/document_loader.py 

            Mô tả file: None 

            Các class trong file: ['ReadData'] 

            Các hàm lẻ trong file: [] 

            Chỉ đọc: False 
### Tên Lớp: ReadData 

            Mô tả lớp: Lớp được dùng để đọc dữ liệu từ các file PDF trong một thư mục, làm sạch văn bản và lưu trữ nội dung đã đọc. 

            Các lớp được lớp này thừa kế: [] 

            Các hàm trong lớp này: ['__init__', '_clean_text', 'read_pdf', 'write_text_to_file', 'read_out_text'] 

            Chỉ đọc: False 
#### Tên hàm: __init__ 

                Decorator: [] 

                Mô tả hàm: None 

                Chỉ đọc: False 
#### Tên hàm: _clean_text 

                Decorator: [] 

                Mô tả hàm: None 

                Chỉ đọc: False 
#### Tên hàm: read_pdf 

                Decorator: [] 

                Mô tả hàm: Đọc tất cả file PDF trong thư mục và trả về nội dung đã làm sạch. 

                Chỉ đọc: False 
#### Tên hàm: write_text_to_file 

                Decorator: [] 

                Mô tả hàm: Ghi text đã đọc ra thư mục txt để tiện tra cứu. 

                Chỉ đọc: False 
#### Tên hàm: read_out_text 

                Decorator: [] 

                Mô tả hàm: Đọc tất cả file txt trong thư mục đầu ra và trả về nội dung và tên file. 

                Chỉ đọc: False 
## Tên file: rag_project/src/generator.py 

            Mô tả file: None 

            Các class trong file: ['QueryGenerator'] 

            Các hàm lẻ trong file: [] 

            Chỉ đọc: False 
### Tên Lớp: QueryGenerator 

            Mô tả lớp: Lớp dùng để tạo các truy vấn và câu trả lời độc lập bằng cách sử dụng các mô hình ngôn ngữ lớn (LLM) và quản lý lịch sử trò chuyện. 

            Các lớp được lớp này thừa kế: [] 

            Các hàm trong lớp này: ['__init__', '_start_chat_history', '_get_standalone_query', 'generate_answer', 'extract_triplets_from_chunk', 'summary_nodes', 'graph_search_answer'] 

            Chỉ đọc: False 
#### Tên hàm: __init__ 

                Decorator: [] 

                Mô tả hàm: None 

                Chỉ đọc: False 
#### Tên hàm: _start_chat_history 

                Decorator: [] 

                Mô tả hàm: Bắt đầu một phiên chat mới hoặc tiếp tục phiên cũ 

                Chỉ đọc: False 
#### Tên hàm: _get_standalone_query 

                Decorator: [] 

                Mô tả hàm: Tạo câu hỏi độc lập từ câu hỏi mới và lịch sử trò chuyện hiện tại. 

                Chỉ đọc: False 
#### Tên hàm: generate_answer 

                Decorator: [] 

                Mô tả hàm: Tạo câu trả lời dựa trên câu hỏi và ngữ cảnh, đồng thời lưu lịch sử trò chuyện. 

                Chỉ đọc: False 
#### Tên hàm: extract_triplets_from_chunk 

                Decorator: [] 

                Mô tả hàm: Dùng LLM để rút trích các cặp (Subject - Predicate - Object) từ đoạn văn. 

                Chỉ đọc: False 
#### Tên hàm: summary_nodes 

                Decorator: [] 

                Mô tả hàm: Tóm tắt các nodes dựa trên danh sách các mối quan hệ (edges) đã trích xuất. 

                Chỉ đọc: False 
#### Tên hàm: graph_search_answer 

                Decorator: [] 

                Mô tả hàm: Tạo câu trả lời tổng hợp dựa trên các tóm tắt tri thức từ toàn bộ cuốn sách. 

                Chỉ đọc: False 
## Tên file: rag_project/src/graphRAG.py 

            Mô tả file: None 

            Các class trong file: ['GraphRAGManager'] 

            Các hàm lẻ trong file: [] 

            Chỉ đọc: False 
### Tên Lớp: GraphRAGManager 

            Mô tả lớp: Lớp quản lý đồ thị tri thức cho các tác vụ RAG (Retrieval-Augmented Generation). 

            Các lớp được lớp này thừa kế: [] 

            Các hàm trong lớp này: ['__init__', '_read_graph', '_write_graph', 'is_graph_built', 'build_knowledge_graph', 'global_search_answer'] 

            Chỉ đọc: False 
#### Tên hàm: __init__ 

                Decorator: [] 

                Mô tả hàm: None 

                Chỉ đọc: False 
#### Tên hàm: _read_graph 

                Decorator: [] 

                Mô tả hàm: Đọc đồ thị tri thức và các tóm tắt cộng đồng từ file pickle. 

                Chỉ đọc: False 
#### Tên hàm: _write_graph 

                Decorator: [] 

                Mô tả hàm: Ghi đồ thị tri thức và các tóm tắt cộng đồng vào file pickle. 

                Chỉ đọc: False 
#### Tên hàm: is_graph_built 

                Decorator: [] 

                Mô tả hàm: Kiểm tra xem đồ thị tri thức đã được xây dựng và lưu vào cache hay chưa. 

                Chỉ đọc: False 
#### Tên hàm: build_knowledge_graph 

                Decorator: [] 

                Mô tả hàm: Xây dựng đồ thị tri thức từ các chunks và lưu vào cache. 

                Chỉ đọc: False 
#### Tên hàm: global_search_answer 

                Decorator: [] 

                Mô tả hàm: Trả lời các câu hỏi tóm tắt toàn bộ tài liệu dựa trên các Community Summaries. 

                Chỉ đọc: False 
## Tên file: rag_project/src/rag_pipeline.py 

            Mô tả file: None 

            Các class trong file: ['RAG_System'] 

            Các hàm lẻ trong file: [] 

            Chỉ đọc: False 
### Tên Lớp: RAG_System 

            Mô tả lớp: Lớp quản lý toàn bộ hệ thống RAG (Retrieval-Augmented Generation), bao gồm việc nạp tài liệu, truy vấn và quản lý đồ thị tri thức. 

            Các lớp được lớp này thừa kế: [] 

            Các hàm trong lớp này: ['__init__', 'ingest_documents', 'query', 'run_terminal'] 

            Chỉ đọc: False 
#### Tên hàm: __init__ 

                Decorator: [] 

                Mô tả hàm: None 

                Chỉ đọc: False 
#### Tên hàm: ingest_documents 

                Decorator: [] 

                Mô tả hàm: Thêm tài liệu vào hệ thống RAG, bao gồm đọc PDF, tách văn bản, xây dựng chỉ mục và (tùy chọn) xây dựng đồ thị tri thức. 

                Chỉ đọc: False 
#### Tên hàm: query 

                Decorator: [] 

                Mô tả hàm: Xử lý câu hỏi từ người dùng, xác định chế độ (toàn cục hoặc cục bộ), và trả về câu trả lời cùng với ngữ cảnh. 

                Chỉ đọc: False 
#### Tên hàm: run_terminal 

                Decorator: [] 

                Mô tả hàm: Chạy hệ thống RAG trong chế độ terminal, cho phép người dùng nhập câu hỏi và nhận câu trả lời. 

                Chỉ đọc: False 
## Tên file: rag_project/src/retriever.py 

            Mô tả file: None 

            Các class trong file: ['HybridRetriever'] 

            Các hàm lẻ trong file: [] 

            Chỉ đọc: False 
### Tên Lớp: HybridRetriever 

            Mô tả lớp: Lớp để quản lý việc truy xuất thông tin từ cơ sở dữ liệu vector, kết hợp giữa dense retrieval (Chroma DB) và sparse retrieval (BM25). 

            Các lớp được lớp này thừa kế: [] 

            Các hàm trong lớp này: ['__init__', '_generate_chunk_id', '_load_cache', '_save_cache', '__sigmoid', 'build_index', 'load_index', 'retriever'] 

            Chỉ đọc: False 
#### Tên hàm: __init__ 

                Decorator: [] 

                Mô tả hàm: None 

                Chỉ đọc: False 
#### Tên hàm: _generate_chunk_id 

                Decorator: ['staticmethod'] 

                Mô tả hàm: Tạo một ID duy nhất cho mỗi chunk dựa trên hash SHA-256 của nội dung chunk. 

                Chỉ đọc: False 
#### Tên hàm: _load_cache 

                Decorator: [] 

                Mô tả hàm: Tải cache BM25 từ file pickle nếu tồn tại. Trả về True nếu tải thành công, False nếu không có cache. 

                Chỉ đọc: False 
#### Tên hàm: _save_cache 

                Decorator: [] 

                Mô tả hàm: Lưu cache BM25 vào file pickle để sử dụng lại sau này. 

                Chỉ đọc: False 
#### Tên hàm: __sigmoid 

                Decorator: ['staticmethod'] 

                Mô tả hàm: None 

                Chỉ đọc: False 
#### Tên hàm: build_index 

                Decorator: [] 

                Mô tả hàm: Xây dựng chỉ mục vector từ các chunks và lưu vào Chroma DB, đồng thời cập nhật cache BM25. 

                Chỉ đọc: False 
#### Tên hàm: load_index 

                Decorator: [] 

                Mô tả hàm: Tải chỉ mục từ Chroma DB và cache BM25 nếu tồn tại. 

                Chỉ đọc: False 
#### Tên hàm: retriever 

                Decorator: [] 

                Mô tả hàm: Retriever sử dụng percentile-based selection để chọn chunks tốt nhất.

Args:
    question: Câu hỏi cần trả lời
    top_k: Số lượng ứng viên tối đa để rerank
    final_top_k: Số lượng chunks tối đa để trả về
    k_min: Số lượng chunks tối thiểu để trả về
    rrf_k: Tham số RRF fusion
    score_percentile: Ngưỡng percentile (0-1) để giữ lại chunks. Default: 0.75 (giữ top 75%) 

                Chỉ đọc: False 
## Tên file: rag_project/src/text_splitter.py 

            Mô tả file: None 

            Các class trong file: ['TextSplitter'] 

            Các hàm lẻ trong file: [] 

            Chỉ đọc: False 
### Tên Lớp: TextSplitter 

            Mô tả lớp: Lớp để tách văn bản thành các chunks nhỏ hơn, phục vụ cho việc truy xuất thông tin và xây dựng chỉ mục. 

            Các lớp được lớp này thừa kế: [] 

            Các hàm trong lớp này: ['__init__', 'split_texts'] 

            Chỉ đọc: False 
#### Tên hàm: __init__ 

                Decorator: [] 

                Mô tả hàm: None 

                Chỉ đọc: False 
#### Tên hàm: split_texts 

                Decorator: [] 

                Mô tả hàm: Tách danh sách văn bản thành các chunks nhỏ hơn dựa trên kích thước và độ chồng lấp đã định nghĩa.
Args:
    texts: Danh sách các văn bản cần tách.
    names: Danh sách tên tương ứng với mỗi văn bản (tùy chọn).  

                Chỉ đọc: False 
## Tên file: rag_project/src/__init__.py 

            Mô tả file: None 

            Các class trong file: [] 

            Các hàm lẻ trong file: [] 

            Chỉ đọc: False 
## Tên file: rag_project/tests/query_data_test.py 

            Mô tả file: None 

            Các class trong file: [] 

            Các hàm lẻ trong file: [] 

            Chỉ đọc: False 
## Tên file: rag_project/tests/test_env.py 

            Mô tả file: None 

            Các class trong file: [] 

            Các hàm lẻ trong file: [] 

            Chỉ đọc: False 
## Tên file: rag_project/tests/test_graph_rag.py 

            Mô tả file: None 

            Các class trong file: ['TestGraphRAG'] 

            Các hàm lẻ trong file: [] 

            Chỉ đọc: False 
### Tên Lớp: TestGraphRAG 

            Mô tả lớp: None 

            Các lớp được lớp này thừa kế: ['unittest.TestCase'] 

            Các hàm trong lớp này: ['test_extract_triplets_handles_ollama_message_shape', 'test_build_knowledge_graph_writes_summary_and_graph', 'test_global_search_answer_returns_tuple_when_no_summaries'] 

            Chỉ đọc: False 
#### Tên hàm: test_extract_triplets_handles_ollama_message_shape 

                Decorator: [] 

                Mô tả hàm: None 

                Chỉ đọc: False 
#### Tên hàm: test_build_knowledge_graph_writes_summary_and_graph 

                Decorator: [] 

                Mô tả hàm: None 

                Chỉ đọc: False 
#### Tên hàm: test_global_search_answer_returns_tuple_when_no_summaries 

                Decorator: [] 

                Mô tả hàm: None 

                Chỉ đọc: False 
## Tên file: rag_project/tests/translate.py 

            Mô tả file: None 

            Các class trong file: [] 

            Các hàm lẻ trong file: [] 

            Chỉ đọc: False 
## Tên file: rag_project/web/UI.py 

            Mô tả file: None 

            Các class trong file: ['ChatRequest', 'ChatResponse'] 

            Các hàm lẻ trong file: ['root', 'health_check', 'test_endpoint', 'chat_endpoint'] 

            Chỉ đọc: False 
### Tên Lớp: ChatRequest 

            Mô tả lớp: None 

            Các lớp được lớp này thừa kế: ['BaseModel'] 

            Các hàm trong lớp này: [] 

            Chỉ đọc: False 
### Tên Lớp: ChatResponse 

            Mô tả lớp: None 

            Các lớp được lớp này thừa kế: ['BaseModel'] 

            Các hàm trong lớp này: [] 

            Chỉ đọc: False 
#### Tên hàm: root 

                Decorator: [] 

                Mô tả hàm: Serve the main HTML page 

                Chỉ đọc: False 
#### Tên hàm: health_check 

                Decorator: [] 

                Mô tả hàm: Health check endpoint 

                Chỉ đọc: False 
#### Tên hàm: test_endpoint 

                Decorator: [] 

                Mô tả hàm: Simple test endpoint to diagnose issues 

                Chỉ đọc: False 
#### Tên hàm: chat_endpoint 

                Decorator: [] 

                Mô tả hàm: None 

                Chỉ đọc: False 
