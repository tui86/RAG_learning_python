from __future__ import annotations

from typing import List, Dict

from deep_translator import GoogleTranslator
from google import genai
import ollama
import re
import json

from .config import get_env, logger
from database.chat_history import ChatHistory

class QueryGenerator:
    '''Lớp dùng để tạo các truy vấn và câu trả lời độc lập bằng cách sử dụng các mô hình ngôn ngữ lớn (LLM) và quản lý lịch sử trò chuyện.'''
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or get_env("GOOGLE_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        self.translator = GoogleTranslator(source="vi", target="en")
        self.current_history_chat: List[Dict[str, str]] = []
        self.history_chat = ChatHistory()
        self.current_session_id = None
        self.current_user_id = None

    def _start_chat_history(self, session_id: str = None):
        """Bắt đầu một phiên chat mới hoặc tiếp tục phiên cũ"""        
        if session_id:
            self.current_session_id = session_id
            logger.info(f"Tiếp tục phiên chat: {session_id} User: {self.current_user_id}")
        else:
            self.current_session_id = self.history_chat.create_new_session(user_id=self.current_user_id)

    def _get_standalone_query(self, question: str) -> str:
        '''Tạo câu hỏi độc lập từ câu hỏi mới và lịch sử trò chuyện hiện tại.'''
        if not self.current_session_id:
            return self.translator.translate(question)

        self.current_history_chat = self.history_chat.get_chat_history(self.current_session_id, limit=6)
        history_str = "".join(
            f"{'Người dùng' if msg['role'] == 'user' else 'Hệ thống'}: {msg['text']}\n"
            for msg in self.current_history_chat
        )

        prompt = f"""Bạn là một mô hình chuyển hóa câu hỏi cho hệ thống tìm kiếm tài liệu.

Hãy viết lại câu hỏi mới thành một câu hỏi độc lập (standalone question) đủ ngữ cảnh để hệ thống có thể tìm kiếm tài liệu mà không cần lịch sử trò chuyện.

Yêu cầu:
- Nếu câu hỏi mới đã đủ rõ ràng và không phụ thuộc vào lịch sử, hãy giữ nguyên câu hỏi đó.
- Nếu câu hỏi có tham chiếu như "nó", "đó", "họ", "cái này", hãy thay bằng các đối tượng cụ thể từ lịch sử khi có thể.
- Chỉ dùng thông tin có trong lịch sử trò chuyện và câu hỏi mới; tuyệt đối không suy đoán hoặc thêm thông tin mới.
- Không trả lời câu hỏi, không giải thích, không đưa ra bình luận.
- Chỉ trả về một câu hỏi duy nhất, không kèm nhãn, không kèm lời dẫn, không kèm markdown.
- Nếu việc tạo câu hỏi mới khiến nghĩa thay đổi, hãy giữ nguyên câu hỏi gốc.
- Câu hỏi phải là tiếng Anh.

[Lịch sử trò chuyện]:
{history_str}

[Câu hỏi mới]:
{question}

Câu hỏi độc lập:"""
        if not self.client:
            return self.translator.translate(question)

        try:
            response = self.client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            standalone_query = response.text.strip()
            logger.info("Câu hỏi được tổng hợp: %s", standalone_query)
            return standalone_query
        except Exception:
            logger.exception("Không thể tạo câu hỏi độc lập, dùng bản dịch thay thế")
            return self.translator.translate(question)

    def generate_answer(self, question: str, context: str) -> str:
        '''Tạo câu trả lời dựa trên câu hỏi và ngữ cảnh, đồng thời lưu lịch sử trò chuyện.'''
        prompt = f"""Bạn là một trợ lý làm việc nghiêm ngặt và chú trọng việc trích dẫn nguồn cho một cơ sở tri thức nội bộ.

CÁC QUY TẮC:
1) CHỈ sử dụng ngữ cảnh được cung cấp để trả lời.
2) Nếu context liên quan nhưng chưa đủ trực tiếp, hãy cố gắng trả lời dựa trên thông tin gần nhất trong context.
3) KHÔNG sử dụng kiến thức bên ngoài, phỏng đoán hay thông tin từ web.
4) Nếu có thể, hãy trích dẫn nguồn theo định dạng (nguồn:trang) dựa trên dữ liệu đi kèm.
5) Câu trả lời đó phải được dịch sang Tiếng Việt.

[Ngữ cảnh]:
{context}

[Câu hỏi của người dùng]:
{question}

Trả lời:"""
        if not self.client:
            return "Cấu hình GEMINI_API_KEY chưa sẵn sàng."

        self._start_chat_history(self.current_session_id)
         
        try:
            response = self.client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            answer_text = response.text
            self.history_chat.add_message(session_id=self.current_session_id, role='user', text=question)
            self.history_chat.add_message(session_id=self.current_session_id, role='model', text=answer_text)
            return answer_text
        except Exception as exc:
            logger.exception("Không thể sinh câu trả lời: %s", exc)
            return "Tôi không thể tạo câu trả lời lúc này."

    def extract_triplets_from_chunk(self, chunk_text: str) -> list[dict]:
        """Dùng LLM để rút trích các cặp (Subject - Predicate - Object) từ đoạn văn."""
        promt = f"""Bạn là chuyên gia Phân tích Đồ thị Tri thức (Knowledge Graph Extraction).
            Nhiệm vụ: Đọc đoạn văn bản và trích xuất các Thực thể (Entities) và Mối quan hệ (Relationships) chính.

            ĐỊNH DẠNG ĐẦU RA (Đúng cấu trúc JSON Array, không thêm lời dẫn, không markdown block):
            [
            {{"source": "Sparse Matrix", "relation": "IS_A_TYPE_OF", "target": "Matrix"}},
            {{"source": "CSR Method", "relation": "STORES", "target": "Non-zero Values"}}
            ]

            VĂN BẢN:
            {chunk_text}

            JSON ARRAY:"""

        try:
            response = ollama.chat(model='qwen2.5', messages=[{'role': 'user', 'content': promt}])

            response_text = response.message.content.strip()
            print(f"response_text: {response_text}")
            response_json = re.sub(r'^```json\s*|\s*```$', '', response_text, flags=re.MULTILINE)
            response_json = re.search(r'\[.*\]', response_text, re.DOTALL)
            print(f"response_json: {response_json}")
            if response_json:
                json_str = response_json.group(0)
                print(f"json_str: {json_str}")
                triplets = json.loads(json_str)
                print(f"triplets: {triplets}")

                return triplets if isinstance(triplets, list) else []
            else:
                return []

        except Exception as e:
            logger.info(f"Không thể trích xuất triplets từ chunk, trả về danh sách rỗng, lỗi {e}")
            return []

    def summary_nodes(self, edges_text: str) -> str:
        '''Tóm tắt các nodes dựa trên danh sách các mối quan hệ (edges) đã trích xuất.'''
        promt = f"""Tóm tắt ngắn gọn các chủ đề và tri thức chính dựa trên danh sách các mối quan hệ dưới đây: 
        {edges_text} 
        Bản Tóm Tắt Chủ Đề:"""
        try:
            response = ollama.chat(model='qwen2.5', messages=[{'role':'user', 'content': promt}])
            response_text = response.message.content.strip()
            return response_text
        except Exception as e:
            logger.info(f"Không thể tóm tắt các nodes, trả về chuỗi rỗng, lỗi {e}")
        return ''

    def graph_search_answer(self, question: str, summaries_text: str) -> str:
        '''Tạo câu trả lời tổng hợp dựa trên các tóm tắt tri thức từ toàn bộ cuốn sách.'''

        prompt = f"""Bạn là một trợ lý AI chuyên tóm tắt và tổng hợp tri thức cấp độ toàn cục (Global Summary).
        Dựa trên Tóm tắt của các Cụm Tri thức trích xuất từ toàn bộ cuốn sách, hãy trả lời câu hỏi của người dùng một cách bao quát, cấu trúc và chi tiết nhất.

        TÓM TẮT CÁC CỤM TRI THỨC TRONG SÁCH:
        {summaries_text}

        CÂU HỎI TỔNG QUAN:
        {question}

        CÂU TRẢ LỜI TỔNG HỢP (TIẾNG VIỆT):"""

        try:
            response = self.client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            answer_text = response.text
            self.current_history_chat.append({"role": "user", "text": question})
            self.current_history_chat.append({"role": "model", "text": answer_text})
            if len(self.current_history_chat) > 10:
                self.current_history_chat = self.current_history_chat[-10:]
        except Exception as exc:
            logger.exception("Không thể sinh câu trả lời: %s", exc)
            return "Tôi không thể tạo câu trả lời lúc này."
        return answer_text