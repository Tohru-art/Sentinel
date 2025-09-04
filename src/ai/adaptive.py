"""Adaptive difficulty and weak spot analysis system"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.database.models import get_database_connection
from config import COMPTIA_CERTS

async def update_topic_performance(user_id, certification, topic, is_correct, response_time=30):
    """Update user's performance data for adaptive difficulty"""
    conn = get_database_connection()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        # Get or create topic performance record
        cursor.execute("""
            INSERT INTO topic_performance (user_id, certification, topic, questions_attempted, questions_correct, avg_response_time)
            VALUES (%s, %s, %s, 1, %s, %s)
            ON CONFLICT (user_id, certification, topic)
            DO UPDATE SET
                questions_attempted = topic_performance.questions_attempted + 1,
                questions_correct = topic_performance.questions_correct + %s,
                avg_response_time = (topic_performance.avg_response_time + %s) / 2,
                last_practiced = CURRENT_TIMESTAMP,
                mastery_level = CASE 
                    WHEN topic_performance.questions_attempted + 1 >= 5 THEN
                        (topic_performance.questions_correct + %s) / CAST(topic_performance.questions_attempted + 1 AS DECIMAL)
                    ELSE topic_performance.mastery_level
                END,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, certification, topic, 1 if is_correct else 0, response_time, 
              1 if is_correct else 0, response_time, 1 if is_correct else 0))
        
        conn.commit()
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error updating topic performance: {e}")
        if conn:
            conn.close()

async def get_adaptive_difficulty(user_id, certification, topic):
    """Calculate optimal difficulty for user based on performance"""
    conn = get_database_connection()
    if not conn:
        return "intermediate"
    
    try:
        cursor = conn.cursor()
        
        # Get topic performance
        cursor.execute("""
            SELECT questions_attempted, questions_correct, mastery_level, current_difficulty
            FROM topic_performance
            WHERE user_id = %s AND certification = %s AND topic = %s
        """, (user_id, certification, topic))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not result or result['questions_attempted'] < 3:
            return "intermediate"  # Default for new users
        
        mastery = result['mastery_level']
        
        # Adaptive difficulty logic
        if mastery >= 0.85:  # 85%+ accuracy
            return "advanced"
        elif mastery >= 0.65:  # 65%+ accuracy 
            return "intermediate"
        else:  # Below 65% accuracy
            return "beginner"
            
    except Exception as e:
        print(f"❌ Error getting adaptive difficulty: {e}")
        return "intermediate"

async def get_weak_spots(user_id, certification, limit=5):
    """Identify user's weakest topics for targeted practice"""
    conn = get_database_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT topic, questions_attempted, questions_correct, mastery_level,
                   ROUND(CAST((questions_correct * 100.0 / questions_attempted) AS NUMERIC), 1) as accuracy
            FROM topic_performance
            WHERE user_id = %s AND certification = %s AND questions_attempted >= 3
            ORDER BY mastery_level ASC, accuracy ASC
            LIMIT %s
        """, (user_id, certification, limit))
        
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        return result
        
    except Exception as e:
        print(f"❌ Error getting weak spots: {e}")
        if conn:
            conn.close()
        return []

async def get_user_strengths(user_id, certification, limit=5):
    """Get user's strongest topics for confidence building"""
    conn = get_database_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT topic, questions_attempted, questions_correct, mastery_level,
                   ROUND(CAST((questions_correct * 100.0 / questions_attempted) AS NUMERIC), 1) as accuracy
            FROM topic_performance
            WHERE user_id = %s AND certification = %s AND questions_attempted >= 3
            ORDER BY mastery_level DESC, accuracy DESC
            LIMIT %s
        """, (user_id, certification, limit))
        
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        return result
        
    except Exception as e:
        print(f"❌ Error getting strengths: {e}")
        if conn:
            conn.close()
        return []