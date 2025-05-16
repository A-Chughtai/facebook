import sqlite3
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_database():
    # Get database path from environment variable or use default
    db_path = os.getenv("DB_PATH", "db/social_media.db")
    
    # Create db directory if it doesn't exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Connect to SQLite database (creates it if it doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Drop existing tables if they exist
    cursor.execute('DROP TABLE IF EXISTS POSTS')
    cursor.execute('DROP TABLE IF EXISTS USER')
    
    # Create USER table
    cursor.execute('''
    CREATE TABLE USER (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fb_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        wa_no TEXT
    )
    ''')
    
    # Create POSTS table
    cursor.execute('''
    CREATE TABLE POSTS (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        username TEXT NOT NULL,
        post_id TEXT UNIQUE NOT NULL,
        post_text TEXT NOT NULL,
        message_sent BOOLEAN DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES USER(fb_id)
    )
    ''')
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print("Database tables created successfully!")

if __name__ == "__main__":
    create_database() 