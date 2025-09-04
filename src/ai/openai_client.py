"""OpenAI integration for AI-powered features"""
import openai
import os
from config import COMPTIA_CERTS

# Initialize OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = None

if OPENAI_API_KEY:
    openai_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    print("🤖 OpenAI Integration: ✅ Enabled")
else:
    print("🤖 OpenAI Integration: ❌ Disabled (No API key)")

async def extract_topic_from_question(question_text, certification):
    """Use AI to extract the main topic/domain from a question"""
    if not openai_client:
        return "General"
    
    try:
        cert_domains = COMPTIA_CERTS[certification]['domains']
        domains_list = ", ".join(cert_domains)
        
        prompt = f"""Question: {question_text}
        
From this CompTIA {certification} question, identify which domain/topic it belongs to.
Available domains: {domains_list}

Respond with just the domain name, nothing else."""
        
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
            temperature=0.1
        )
        
        topic = response.choices[0].message.content.strip()
        # Validate topic is in our domains list
        if topic in cert_domains:
            return topic
        else:
            # Find closest match
            for domain in cert_domains:
                if any(word.lower() in topic.lower() for word in domain.split()):
                    return domain
            return cert_domains[0]  # Default to first domain
            
    except Exception as e:
        print(f"❌ Topic extraction error: {e}")
        return "General"

async def generate_study_recommendations(user_id, certification, weak_spots, strengths):
    """Generate personalized AI study recommendations"""
    if not openai_client or not weak_spots:
        return "Continue practicing with `/practice` to unlock AI recommendations!"
    
    try:
        weak_topics = [spot['topic'] for spot in weak_spots[:3]]
        weak_text = ", ".join(weak_topics)
        
        prompt = f"""CompTIA {certification} study focus needed: {weak_text}

Generate exactly 3 bullet points. Each bullet point must be:
- Maximum 8 words
- Start with action verb
- No explanations

Format: 
• [action verb] [topic] [method/resource]
• [action verb] [topic] [method/resource] 
• [action verb] [topic] [method/resource]"""
        
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=80,
            temperature=0.2
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"❌ Recommendation error: {e}")
        return "Focus on your identified weak spots with targeted practice sessions."