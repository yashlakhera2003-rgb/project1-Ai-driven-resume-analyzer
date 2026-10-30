import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """Establishes a connection to the cloud Aiven MySQL instance"""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 22008)), # Aiven defaults to port 22008
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

def init_db():
    """Creates the analysis storage table with email column on Aiven Cloud"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resume_results (
            id INT AUTO_INCREMENT PRIMARY KEY,
            candidate_name VARCHAR(255),
            candidate_email VARCHAR(255),
            match_score INT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("Database initialized successfully on Aiven Cloud!")

# Automatically runs and creates the table online when imported
init_db()
