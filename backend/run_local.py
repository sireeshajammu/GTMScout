"""Local dev server.  Run:  python run_local.py   (serves http://localhost:8000)"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
