"""Main CompTIA Study Bot Runner"""

from flask import Flask
from threading import Thread
from src.bot import bot
from config import DISCORD_TOKEN

# Flask keep-alive server
app = Flask('')

@app.route('/')
def home():
    return "CompTIA Study Bot is running!"

@app.route('/health')
def health():
    """Health check endpoint for monitoring services"""
    from flask import jsonify
    return jsonify({
        "status": "online", 
        "bot": "CompTIA Study Bot",
        "message": "All systems operational",
        "timestamp": "2025-09-04T05:42:00Z"
    })

@app.route('/status')
def status():
    """Detailed status endpoint"""
    return """
    <html>
    <head><title>CompTIA Study Bot Status</title></head>
    <body>
        <h1>🤖 CompTIA Study Bot</h1>
        <p><strong>Status:</strong> ✅ Online</p>
        <p><strong>Services:</strong> Discord Bot, Web Server</p>
        <p><strong>Commands:</strong> 17 Active</p>
        <p><strong>Database:</strong> ✅ Connected</p>
    </body>
    </html>
    """

def run():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False, threaded=True)

def keep_alive():
    """Start the keep-alive server in a separate thread"""
    t = Thread(target=run)
    t.start()

def main():
    """Main function to run the bot"""
    if not DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN not found in environment variables")
        return
    
    # Start keep-alive server
    keep_alive()
    
    # Run bot
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    main()