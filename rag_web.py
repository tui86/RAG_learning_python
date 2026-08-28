from pathlib import Path
import uvicorn
from web.UI import app

if __name__ == "__main__":
    # Run the FastAPI application
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )

