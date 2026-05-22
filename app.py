import uvicorn
from backend.main import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run("app:app", host="::", port=8000, reload=True)
