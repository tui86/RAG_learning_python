from pymongo import MongoClient
import uuid
import datetime
import certifi
from urllib.parse import urlparse

from src.config import get_env, logger

class ChatHistory:
    '''Lớp quản lí dữ liệu từ MongoDB.'''
    def __init__(self, host: str = "mongodb://localhost:27017/", db_name: str = "rag_chat_bot"):
        self.host = get_env(name='DATABASE') or host
        parsed_host = urlparse(self.host).hostname
        client_options = {}
        if parsed_host not in {"localhost", "127.0.0.1", "::1"}:
            client_options["tlsCAFile"] = certifi.where()
        self.client = MongoClient(host=self.host, **client_options)
        self.db = self.client[db_name]
        self.collection = self.db['chat_sessions']
        self.collection.create_index('session_id', unique = True)

    def create_new_session(self, user_id: str = 'default_user') -> str:
        """Tạo một phiên chat (session) mới và trả về session_id."""
        if user_id is None:
            user_id = 'default_user'

        session_id = str(uuid.uuid4())
        session_data = {
            'session_id': session_id,
            'user_id': user_id,
            'create_at': datetime.datetime.now(datetime.timezone.utc),
            'messages': []
        }
        self.collection.insert_one(session_data)
        return session_id

    def add_message(self, session_id: str, role: str, text: str):
        """
        Thêm một tin nhắn (của 'user' hoặc 'model') vào một phiên chat đã tồn tại.
        Sử dụng toán tử $push của MongoDB để chỉ cập nhật mảng 'messages', không ghi đè toàn bộ document.
        """        
        message_data = {
            'role': role,
            'text': text,
            'timestamp': datetime.datetime.now(datetime.timezone.utc)
        }
        result = self.collection.update_one(
            {'session_id': session_id},
            {'$push': {'messages': message_data}}
        )
        if result.modified_count == 0:
            logger.info(f'Không tìm thấy session_id {session_id} để lưu tin nhắn')

    def get_chat_history(self, session_id: str, limit: int = 10) -> list:
        """
        Truy xuất lịch sử chat của một phiên (session_id).
        Trả về `limit` tin nhắn gần nhất để nạp vào Context Window của LLM.
        """        
        session = self.collection.find_one(
            {'session_id': session_id},
            {'_id': 0, 'messages': 1}
        )
        if not session or 'messages' not in session:
            return []
        messages = session['messages']
        if limit <= 0:
            return []
        return messages[-limit:]

    def get_all_sessions(self, user_id: str) -> list:
        """Lấy danh sách các phiên chat của một user để hiển thị trên UI (như sidebar của ChatGPT)"""
        sessions = self.collection.find({'user_id': user_id},
                                        {'_id': 0, 'session_id': 1, 'create_at': 1}
                                        ).sort('create_at', -1)
        return list(sessions)