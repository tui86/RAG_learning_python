from __future__ import annotations

from typing import List, Dict

from google import genai
import ollama
import re
import json
import torch

from .config import get_env, logger
from database.chat_history import ChatHistory
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

class LocalTranslator:
    def __init__(self):
        self.model_name = "Helsinki-NLP/opus-mt-vi-en"

        self.device = ( "cuda" if torch.cuda.is_available() else "cpu")

        print(f"Loading translation model on {self.device}...")

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)

        self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)

        self.model.to(self.device)
        self.model.eval()

        print("Translation model loaded.")

    @torch.inference_mode()
    def translate(self, text: str) -> str:
        if not isinstance(text, str):
            raise TypeError("text must be a string")

        text = text.strip()

        if not text:
            return ""

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        )

        inputs = {
            key: value.to(self.device)
            for key, value in inputs.items()
        }

        output = self.model.generate(
            **inputs,
            max_new_tokens=256,
            num_beams=4,
        )

        translated = self.tokenizer.decode(
            output[0],
            skip_special_tokens=True,
        )

        if not translated.strip():
            raise RuntimeError("Translation returned empty text.")

        return translated.strip()

class QueryGenerator:
    '''Lớp dùng để tạo các truy vấn và câu trả lời độc lập bằng cách sử dụng các mô hình ngôn ngữ lớn (LLM) và quản lý lịch sử trò chuyện.'''
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or get_env("GOOGLE_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        self.translator = LocalTranslator() 
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

    def _translate_question(self, question: str) -> str:
        try:
            print(f"Translating question: {question}")
            return self.translator.translate(question)
        except Exception:
            logger.exception("Không thể dịch câu hỏi, dùng câu hỏi gốc để truy hồi")
            return question

    def _get_standalone_query(self, question: str) -> str:
        '''Tạo câu hỏi độc lập từ câu hỏi mới và lịch sử trò chuyện hiện tại.'''
        if not self.current_session_id:
            return self._translate_question(question)

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
            return self._translate_question(question)

        try:
            response = self.client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            standalone_query = response.text.strip()
            logger.info("Câu hỏi được tổng hợp: %s", standalone_query)
            return standalone_query
        except Exception:
            logger.exception("Không thể tạo câu hỏi độc lập, dùng bản dịch thay thế")
            return self._translate_question(question)

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
        promt = f"""You are an expert in Knowledge Graph Extraction.
        Task: Extract entities and relationships from the text below.
        STRICT RULES:
        1. Return the output in JSON or CSV format: [Source, Relation, Target].
        2. DO NOT use Chinese or foreign languages. All Relations must be written in UPPERCASE ENGLISH (e.g., HAS_PART, IS_ABOUT, USES).
        3. DO NOT include conversational phrases such as "Here is..." or "Sorry...". If no valid entities are found, return an empty array [].
        4. Convert all words to their base forms and use only the simple present tense for the sentences.
            OUTPUT FORMAT (Valid JSON Array structure, no introductory text, no markdown blocks, use only english):
            [
            {{"source": "Sparse Matrix", "relation": "IS_A_TYPE_OF", "target": "Matrix"}},
            {{"source": "CSR Method", "relation": "STORES", "target": "Non-zero Values"}}
            ]

            TEXT:
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
        '''Tóm tắt nội dung section cùng các mối quan hệ đã trích xuất.'''
        promt = f"""
        You are a professional data analysis AI. Synthesize the following section content and relationships into a concise paragraph.

        [SECTION CONTENT AND RELATIONSHIPS]:
        {edges_text}

        MANDATORY RULES (Violation will result in a penalty):
        1. Use ONLY the information contained in the list above. ABSOLUTELY DO NOT use external knowledge from the internet.
        2. ABSOLUTELY DO NOT translate into any language other than Vietnamese; do not use Chinese.
        3. Do not mention the names of online courses (such as edX or Coursera) unless they are explicitly included in the list.
        4. If the data is insufficient or meaningless, return exactly one sentence: "Dữ liệu không đủ để tóm tắt." Do not apologize.
        5. use only simple present tense and avoid using the first person "I" in the summary.
        Your summary:
        """
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