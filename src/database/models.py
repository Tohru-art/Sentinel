"""Database models and operations"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")

def get_database_connection():
    """Get a connection to the PostgreSQL database"""
    try:
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

def initialize_database():
    """Create the database schema if it doesn't exist"""
    if not DATABASE_URL:
        print("⚠️ No database URL configured, skipping database initialization")
        return False
        
    conn = get_database_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        # Create users table for study progress tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username VARCHAR(100),
                selected_cert VARCHAR(50),
                study_streak INTEGER DEFAULT 0,
                total_questions INTEGER DEFAULT 0,
                correct_answers INTEGER DEFAULT 0,
                study_score INTEGER DEFAULT 0,
                study_time_minutes INTEGER DEFAULT 0,
                last_study_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create question_history table for detailed tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS question_history (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                certification VARCHAR(50),
                difficulty VARCHAR(20),
                question_text TEXT,
                user_answer CHAR(1),
                correct_answer CHAR(1),
                is_correct BOOLEAN,
                response_time_seconds INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create study_sessions table for detailed progress tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS study_sessions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                session_type VARCHAR(50),
                duration_minutes INTEGER,
                questions_answered INTEGER DEFAULT 0,
                questions_correct INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create topic_performance table for adaptive difficulty and weak spot analysis
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS topic_performance (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                certification VARCHAR(50),
                topic VARCHAR(100),
                questions_attempted INTEGER DEFAULT 0,
                questions_correct INTEGER DEFAULT 0,
                current_difficulty VARCHAR(20) DEFAULT 'intermediate',
                avg_response_time DECIMAL DEFAULT 0,
                last_practiced TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                mastery_level DECIMAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, certification, topic)
            )
        """)
        
        # Create user_achievements table for gamification
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_achievements (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                achievement_id VARCHAR(100),
                achievement_name VARCHAR(200),
                achievement_description TEXT,
                earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                category VARCHAR(50),
                points INTEGER DEFAULT 0,
                UNIQUE(user_id, achievement_id)
            )
        """)
        
        # Create adaptive_settings table for personalized difficulty
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS adaptive_settings (
                user_id BIGINT PRIMARY KEY REFERENCES users(user_id),
                base_difficulty VARCHAR(20) DEFAULT 'intermediate',
                learning_rate DECIMAL DEFAULT 0.1,
                confidence_threshold DECIMAL DEFAULT 0.75,
                adaptation_speed VARCHAR(20) DEFAULT 'normal',
                preferred_question_types TEXT[],
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ Database schema initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ Database schema creation failed: {e}")
        if conn:
            conn.close()
        return False

async def get_user_data(user_id: int, username: Optional[str] = None):
    """Get or create user data from database"""
    conn = get_database_connection()
    if not conn:
        # Fallback to in-memory for backward compatibility
        return initialize_user_data_memory(user_id)
        
    try:
        cursor = conn.cursor()
        
        # Try to get existing user
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        
        if user:
            # Convert database row to dictionary format matching current system
            user_data = {
                "selected_cert": user['selected_cert'] or "A+",
                "study_streak": user['study_streak'],
                "total_questions": user['total_questions'],
                "correct_answers": user['correct_answers'],
                "study_score": user['study_score'],
                "study_time_minutes": user['study_time_minutes'],
                "last_study_date": user['last_study_date']
            }
        else:
            # Create new user
            cursor.execute("""
                INSERT INTO users (user_id, username, selected_cert, study_streak, 
                                 total_questions, correct_answers, study_score, 
                                 study_time_minutes, last_study_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_id, username, "A+", 0, 0, 0, 0, 0, datetime.utcnow()))
            conn.commit()
            
            user_data = {
                "selected_cert": "A+",
                "study_streak": 0,
                "total_questions": 0,
                "correct_answers": 0,
                "study_score": 0,
                "study_time_minutes": 0,
                "last_study_date": datetime.utcnow()
            }
        
        cursor.close()
        conn.close()
        return user_data
        
    except Exception as e:
        print(f"❌ Error getting user data: {e}")
        if conn:
            conn.close()
        # Fallback to in-memory system
        return initialize_user_data_memory(user_id)

def initialize_user_data_memory(user_id: int) -> Dict[str, Any]:
    """Fallback in-memory user data initialization"""
    return {
        "selected_cert": "A+",
        "study_streak": 0,
        "total_questions": 0,
        "correct_answers": 0,
        "study_score": 0,
        "study_time_minutes": 0,
        "last_study_date": datetime.utcnow()
    }

async def update_user_data(user_id: int, data: dict):
    """Update user data in database"""
    conn = get_database_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        # Update user record
        cursor.execute("""
            UPDATE users SET
                selected_cert = %s,
                study_streak = %s,
                total_questions = %s,
                correct_answers = %s,
                study_score = %s,
                study_time_minutes = %s,
                last_study_date = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
        """, (
            data.get('selected_cert'),
            data.get('study_streak'),
            data.get('total_questions'),
            data.get('correct_answers'),
            data.get('study_score'),
            data.get('study_time_minutes'),
            data.get('last_study_date'),
            user_id
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error updating user data: {e}")
        if conn:
            conn.close()
        return False

# Leaderboard functions
async def get_daily_champions():
    """Get top 5 users by questions answered today"""
    conn = get_database_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.username, u.user_id, COUNT(qh.id) as questions_today
            FROM users u
            LEFT JOIN question_history qh ON u.user_id = qh.user_id 
                AND DATE(qh.created_at) = CURRENT_DATE
            GROUP BY u.user_id, u.username
            HAVING COUNT(qh.id) > 0
            ORDER BY questions_today DESC
            LIMIT 5
        """)
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        return result
    except Exception as e:
        print(f"❌ Error getting daily champions: {e}")
        if conn:
            conn.close()
        return []

async def get_accuracy_masters():
    """Get top 5 users by accuracy rate (minimum 10 questions)"""
    conn = get_database_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.username, u.user_id, 
                   u.total_questions,
                   u.correct_answers,
                   ROUND(CAST((u.correct_answers * 100.0 / u.total_questions) AS NUMERIC), 1) as accuracy
            FROM users u
            WHERE u.total_questions >= 10
            ORDER BY accuracy DESC
            LIMIT 5
        """)
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        return result
    except Exception as e:
        print(f"❌ Error getting accuracy masters: {e}")
        if conn:
            conn.close()
        return []

async def get_study_legends():
    """Get top 5 users by overall study score"""
    conn = get_database_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.username, u.user_id, u.study_score, u.total_questions
            FROM users u
            WHERE u.total_questions > 0
            ORDER BY u.study_score DESC
            LIMIT 5
        """)
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        return result
    except Exception as e:
        print(f"❌ Error getting study legends: {e}")
        if conn:
            conn.close()
        return []