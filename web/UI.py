from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import uuid
import logging
from pathlib import Path
from src.rag_pipeline import RAG_System

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Enterprise RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG system
rag_initialization_error: str | None = None
try:
    rag_system = RAG_System()
    rag_system.retriever.load_index()
    logger.info("✓ RAG System initialized successfully")
except Exception as e:
    rag_initialization_error = f"{type(e).__name__}: {e}"
    logger.exception("✗ Failed to initialize RAG System")
    rag_system = None

class ChatRequest(BaseModel):
    question: str
    mode: str
    session_id: Optional[str] = None
    user_id: str = "web user"

class ChatResponse(BaseModel):
    answer: str
    session_id: Optional[str] = None
    documents: Optional[list] = []

@app.get("/")
async def root():
    """Serve the main HTML page"""
    return FileResponse(Path(__file__).parent / "templates" / "UI.html")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "running",
        "rag_system_initialized": rag_system is not None
    }

@app.get("/api/test")
async def test_endpoint():
    """Simple test endpoint to diagnose issues"""
    return {
        "status": "ok",
        "message": "Server is working!",
        "initialization_error": rag_initialization_error,
        "rag_system": {
            "initialized": rag_system is not None,
            "has_generator": hasattr(rag_system, 'generator') if rag_system else False,
            "has_query_method": hasattr(rag_system, 'query') if rag_system else False
        }
    }

@app.post('/api/chat', response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        # Kiểm tra RAG system
        if rag_system is None:
            logger.error("RAG System not initialized")
            raise HTTPException(status_code=500, detail="RAG System chưa được khởi tạo")
        
        logger.info(f"Received request: question='{request.question}', mode='{request.mode}'")
        
        current_session_id = request.session_id
        
        # Tạo session ID nếu chưa có
        if not current_session_id:
            try:
                # Thử tạo session mới
                if hasattr(rag_system, 'generator') and hasattr(rag_system.generator, 'history_chat'):
                    current_session_id = rag_system.generator.history_chat.create_new_session(user_id=request.user_id)
                    logger.info(f"Created new session: {current_session_id}")
                else:
                    # Fallback: tạo UUID nếu history_chat không tồn tại
                    current_session_id = str(uuid.uuid4())
                    logger.info(f"Using generated UUID as session_id: {current_session_id}")
            except Exception as e:
                logger.warning(f"Could not create session: {str(e)}, using UUID instead")
                current_session_id = str(uuid.uuid4())
        
        # Query RAG system
        try:
            answer = rag_system.query(request.question, request.mode)
            logger.info(f"Query successful for mode '{request.mode}'")
        except Exception as e:
            logger.error(f"Error during query: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Lỗi trong quá trình truy vấn: {str(e)}")
        
        # Extract answer and documents
        if isinstance(answer, dict):
            answer_result = answer.get('answer', 'Không thể xử lý câu hỏi của bạn')
            docs = answer.get('documents', [])
        else:
            answer_result = str(answer)
            docs = []
        
        logger.info(f"Response prepared successfully")
        return ChatResponse(answer=answer_result, session_id=current_session_id, documents=docs)
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

# Mount static files (CSS, JS, etc.)
web_dir = Path(__file__).parent
static_dir = web_dir / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
