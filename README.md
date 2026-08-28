# RAG Project

Hệ thống hỏi đáp tài liệu PDF sử dụng kiến trúc **Retrieval-Augmented Generation (RAG)**. Dự án kết hợp truy xuất dense bằng ChromaDB, truy xuất sparse bằng BM25, mô hình Gemini để sinh câu trả lời và GraphRAG để xử lý các câu hỏi mang tính tổng quan.

## Tính năng

- Đọc và làm sạch nhiều file PDF trong `data/papers/`.
- Chia văn bản thành các đoạn nhỏ để lập chỉ mục.
- Hybrid retrieval: kết hợp ChromaDB và BM25.
- Trả lời câu hỏi cục bộ dựa trên các đoạn văn bản liên quan.
- Xây dựng knowledge graph bằng Ollama và hỗ trợ global search.
- Lưu lịch sử hội thoại vào MongoDB.
- Cung cấp giao diện web FastAPI và chế độ hỏi đáp trên terminal.

## Kiến trúc

```text
PDF files
   |
   v
ReadData -> TextSplitter -> HybridRetriever
                                  |
                                  v
                         ChromaDB + BM25
                                  |
                                  v
                         QueryGenerator
                         (Gemini / Ollama)
                                  |
                                  v
                         FastAPI web UI
```

Các module chính:

| Đường dẫn | Vai trò |
| --- | --- |
| `src/document_loader.py` | Đọc và làm sạch PDF |
| `src/text_splitter.py` | Chia văn bản thành chunks |
| `src/retriever.py` | Lập chỉ mục và hybrid retrieval |
| `src/generator.py` | Dịch câu hỏi, sinh câu trả lời và trích xuất triplets |
| `src/graphRAG.py` | Xây dựng và truy vấn knowledge graph |
| `src/rag_pipeline.py` | Điều phối toàn bộ pipeline RAG |
| `database/chat_history.py` | Lưu lịch sử chat vào MongoDB |
| `web/UI.py` | API FastAPI và giao diện web |

## Yêu cầu

- Python 3.10 trở lên
- MongoDB đang hoạt động hoặc MongoDB Atlas
- API key của Google Gemini cho chức năng sinh câu trả lời
- Ollama và model `qwen2.5` nếu sử dụng GraphRAG

## Cài đặt

```powershell
git clone <repository-url>
cd rag_project
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Nếu PowerShell chặn việc kích hoạt môi trường ảo, chạy trong phiên hiện tại:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

## Cấu hình môi trường

Tạo file `.env` ở thư mục gốc hoặc tạo file bên ngoài rồi trỏ tới nó bằng `RAG_ENV_FILE`:

```env
DATABASE=mongodb://localhost:27017/
GOOGLE_API_KEY=your_google_api_key
LOG_FILE=rag_project.log
```

Không commit file chứa secret. Code mặc định tìm file cấu hình tại `D:\secrets\.env`; có thể ghi đè bằng:

```powershell
$env:RAG_ENV_FILE = "D:\path\to\.env"
```

## Chuẩn bị dữ liệu và lập chỉ mục

Đặt các file PDF cần hỏi đáp vào `data/papers/`. Có thể ingest dữ liệu bằng Python:

```powershell
python -c "from src.rag_pipeline import RAG_System; rag = RAG_System(data_dir='data'); rag.ingest_documents()"
```

Để đồng thời xây dựng knowledge graph:

```powershell
python -c "from src.rag_pipeline import RAG_System; rag = RAG_System(data_dir='data'); rag.ingest_documents(create_knowledge_graph=True)"
```

Index ChromaDB, BM25 cache, graph cache và log sẽ được tạo trong `data/` và đã được thêm vào `.gitignore`.

## Chạy ứng dụng

### Giao diện web

```powershell
python rag_web.py
```

Mở [http://127.0.0.1:8000](http://127.0.0.1:8000). Một số endpoint:

- `GET /api/health`: kiểm tra trạng thái hệ thống.
- `GET /api/test`: kiểm tra khởi tạo RAG.
- `POST /api/chat`: gửi câu hỏi với `question`, `mode`, tùy chọn `session_id` và `user_id`.

Ví dụ request:

```json
{
  "question": "Nội dung chính của tài liệu là gì?",
  "mode": "local"
}
```

`mode` nhận `local` cho truy vấn theo chunks hoặc `global` cho truy vấn dựa trên knowledge graph.

### Terminal

```powershell
python main.py
```

Nhập câu hỏi rồi nhập `exit` để thoát.

## Kiểm thử

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

## Lưu ý bảo mật

- Không ghi API key hoặc chuỗi kết nối MongoDB trực tiếp vào source code.
- Nếu credential từng được commit hoặc chia sẻ, hãy thu hồi và tạo credential mới.
- Dữ liệu PDF trong `data/papers/` có thể chứa nội dung riêng tư; kiểm tra chính sách dữ liệu trước khi đưa lên repository.