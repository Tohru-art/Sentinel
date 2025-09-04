# Sentinel - AI Study Bot

## Project Overview
An advanced AI-powered Discord bot designed for comprehensive study assistance across any subject. The bot provides AI-generated practice questions, explanations, flashcards, cybersecurity tools, and productivity features for students and professionals.

## Features

### AI Learning Tools
- **Smart Practice Questions**: AI-generated multiple-choice questions with detailed explanations
- **Topic Explanations**: Detailed AI explanations for any study subject
- **Flashcards**: Smart flashcard generation for key concepts and terms
- **Study Analytics**: Advanced progress tracking and weak spot analysis
- **Difficulty Levels**: Beginner, Intermediate, and Advanced question difficulty

### Productivity Features
- **Pomodoro Timer**: 25-minute study sessions with 5/15-minute breaks
- **Session Management**: Track active study sessions with progress indicators
- **Break Reminders**: Automated notifications for study session completion

### Cybersecurity Tools
- **Password Strength Analyzer**: Advanced password security analysis with time-to-crack scenarios
- **Cybersecurity Quotes**: Inspirational quotes for motivation
- **Port Scanner**: Network security tool for host/port scanning
- **Hash Generator**: SHA-256 hash generation utility
- **IP Lookup**: Geographic and ISP information lookup

## Technical Stack
- **Language**: Python 3.11
- **Main Libraries**: 
  - discord.py 2.6.3 (Discord API)
  - openai 1.105.0 (AI content generation)
  - flask (Web server for keep-alive)
- **Dependencies**: python-dotenv, requests, asyncio
- **Environment**: Replit with NixOS
- **Database**: In-memory storage (production would use persistent DB)

## Project Structure
```
├── src/                         # Source code directory
│   ├── bot.py                   # Main bot commands (clean & organized)
│   ├── database/
│   │   ├── models.py           # Database operations & user data
│   │   └── achievements.py     # Achievement system
│   ├── ai/
│   │   ├── adaptive.py         # Adaptive difficulty & weak spots
│   │   └── openai_client.py    # OpenAI integration
│   ├── ui/
│   │   └── components.py       # Discord UI components
│   └── utils/
│       └── helpers.py          # Utility functions
├── config.py                   # Configuration and constants
├── main.py                     # Bot runner with Flask keep-alive
├── requirements.txt            # Dependencies
├── .gitignore                 # Git ignore rules
├── pyproject.toml             # Python project config
└── replit.md                  # Project documentation
```

## Available Commands

### Study Commands
- `/certs` - View all available CompTIA certifications
- `/selectcert <certification>` - Choose your CompTIA certification track
- `/studystats` - View comprehensive study progress and statistics

### AI Study Tools
- `/practice [difficulty] [count]` - Generate AI practice questions (1-5)
- `/flashcards [topic] [count]` - Create AI flashcards (1-10)
- `/explain <topic>` - Get detailed AI explanations of topics

### Productivity Tools
- `/pomodoro [session_type]` - Start study/break timer sessions
- `/stoppomodoro` - Stop current Pomodoro session
- `/pomodorostatus` - Check current session progress

### Security Tools  
- `/passwordcheck <password>` - Analyze password strength with time-to-crack scenarios
- `/cyberquote` - Get cybersecurity motivation quotes
- `/scan <host> <port>` - Network port scanning  
- `/hash <text>` - SHA-256 hash generation
- `/iplookup <ip>` - IP address information lookup
- `/ping` - Bot status check

## Current Status
✅ Comprehensive UI makeover with consistent modern styling across all 17 commands
✅ Advanced cybersecurity tools including password analyzer with time-to-crack scenarios
✅ Professional monitoring setup with UptimeRobot JSON health endpoint
✅ All 17 slash commands operational and synced successfully
✅ Rebranded to "Sentinel" - universal AI study bot for any subject
✅ Clean project structure with proper .gitignore
✅ **Ready for GitHub upload** - codebase cleaned and organized

## Recent Changes
- **Universal Rebranding**: Changed to "Sentinel" - AI study bot for any subject (not just CompTIA)
- **GitHub Preparation**: Cleaned up project structure and removed debugging files
- **Complete UI Overhaul**: Applied futuristic, sleek, professional design to all 17 commands
- **Advanced Security Tools**: Password strength analyzer with time-to-crack scenarios and cybersecurity focus
- **Professional Monitoring**: Enhanced health endpoint with JSON status responses for UptimeRobot
- **Modern Design System**: Consistent dark theme (#2B2D31) with professional typography and spacing
- **Code Quality**: Fixed critical LSP diagnostics, production-ready codebase

## Configuration
- **API Keys Required**: 
  - DISCORD_TOKEN (Discord bot authentication)
  - OPENAI_API_KEY (AI content generation)
- **Workflow**: `python main.py`
- **Web Server**: Flask on port 5000 for keep-alive functionality
- **Output**: Console logging with Discord gateway status

## User Data Structure
```python
user_study_data = {
    user_id: {
        "selected_cert": "Security+",
        "study_streak": 5,
        "total_questions": 50,
        "correct_answers": 42,
        "study_time_minutes": 450,
        "last_study_date": datetime
    }
}
```

## AI Integration
The bot uses OpenAI's GPT-3.5-turbo model for:
- Generating realistic exam-style practice questions
- Creating comprehensive flashcards with examples
- Providing detailed topic explanations
- Contextual CompTIA certification-specific content

## Future Enhancements
- Persistent database storage for user data
- Advanced analytics and learning insights
- Spaced repetition algorithms for flashcards
- Integration with real CompTIA practice exams
- Multi-server deployment capabilities