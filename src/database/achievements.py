"""Achievement system for gamification"""
from .models import get_database_connection

# Achievement definitions
ACHIEVEMENTS = {
    # Accuracy Achievements
    "accuracy_master": {
        "name": "Accuracy Master",
        "description": "Maintain 90%+ accuracy over 50+ questions",
        "category": "accuracy",
        "points": 200,
    },
    "perfect_streak": {
        "name": "Perfect Streak",
        "description": "Answer 10 questions correctly in a row",
        "category": "accuracy", 
        "points": 150,
    },
    
    # Volume Achievements
    "question_warrior": {
        "name": "Question Warrior",
        "description": "Answer 100+ practice questions",
        "category": "volume",
        "points": 150,
    },
    "study_legend": {
        "name": "Study Legend", 
        "description": "Answer 500+ practice questions",
        "category": "volume",
        "points": 500,
    },
    
    # Mastery Achievements
    "topic_expert": {
        "name": "Topic Expert",
        "description": "Achieve 85%+ mastery in any topic",
        "category": "mastery",
        "points": 250,
    }
}

async def check_achievements(user_id, certification):
    """Check and award new achievements for user"""
    conn = get_database_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        
        # Get user stats
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user_stats = cursor.fetchone()
        if not user_stats:
            return []
        
        # Get existing achievements
        cursor.execute("SELECT achievement_id FROM user_achievements WHERE user_id = %s", (user_id,))
        existing = [row['achievement_id'] for row in cursor.fetchall()]
        
        new_achievements = []
        
        # Check accuracy master
        if "accuracy_master" not in existing and user_stats['total_questions'] >= 50:
            accuracy = user_stats['correct_answers'] / user_stats['total_questions']
            if accuracy >= 0.9:
                await award_achievement(user_id, "accuracy_master", cursor)
                new_achievements.append(ACHIEVEMENTS["accuracy_master"])
        
        # Check question warrior
        if "question_warrior" not in existing and user_stats['total_questions'] >= 100:
            await award_achievement(user_id, "question_warrior", cursor)
            new_achievements.append(ACHIEVEMENTS["question_warrior"])
        
        # Check study legend
        if "study_legend" not in existing and user_stats['total_questions'] >= 500:
            await award_achievement(user_id, "study_legend", cursor) 
            new_achievements.append(ACHIEVEMENTS["study_legend"])
        
        # Check topic expert
        if "topic_expert" not in existing:
            cursor.execute("""
                SELECT COUNT(*) as count FROM topic_performance 
                WHERE user_id = %s AND certification = %s AND mastery_level >= 0.85
            """, (user_id, certification))
            if cursor.fetchone()['count'] > 0:
                await award_achievement(user_id, "topic_expert", cursor)
                new_achievements.append(ACHIEVEMENTS["topic_expert"])
        
        conn.commit()
        cursor.close()
        conn.close()
        return new_achievements
        
    except Exception as e:
        print(f"❌ Error checking achievements: {e}")
        if conn:
            conn.close()
        return []

async def award_achievement(user_id, achievement_id, cursor):
    """Award an achievement to a user"""
    achievement = ACHIEVEMENTS[achievement_id]
    cursor.execute("""
        INSERT INTO user_achievements (user_id, achievement_id, achievement_name, achievement_description, category, points)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (user_id, achievement_id, achievement['name'], achievement['description'], 
          achievement['category'], achievement['points']))

async def get_user_achievements(user_id):
    """Get all achievements for a user"""
    conn = get_database_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT achievement_name, achievement_description, category, points, earned_at
            FROM user_achievements 
            WHERE user_id = %s
            ORDER BY earned_at DESC
        """, (user_id,))
        
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        return result
        
    except Exception as e:
        print(f"❌ Error getting achievements: {e}")
        if conn:
            conn.close()
        return []