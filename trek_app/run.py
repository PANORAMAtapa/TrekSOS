import os
import sys
import webbrowser
import uvicorn
from database import init_db
from kaggle_parser import seed_database

def start_server():
    print("=" * 65)
    print("TREKQUEST - Smart Mountain GPS & Squad Navigation System")
    print("=" * 65)
    print("Initializing SQLite database & parsing Kaggle trek dataset...")
    
    init_db()
    seed_database()

    print("\nDatabase ready!")
    print("Starting server at: http://127.0.0.1:8000")
    print("Open http://127.0.0.1:8000 in your browser to view the app.")
    print("=" * 65 + "\n")

    # Run Uvicorn server
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)

if __name__ == "__main__":
    start_server()
