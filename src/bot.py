"""Main Discord bot with organized imports and clean command definitions"""
from typing import Optional
import random
import json
import math
import re
import hashlib
import socket
import requests
import asyncio
from datetime import datetime, timedelta

import discord
from discord.ext import commands
from discord import app_commands

# Import our organized modules
from .database.models import (
    initialize_database, get_user_data, update_user_data,
    get_daily_champions, get_accuracy_masters, get_study_legends
)
from .database.achievements import check_achievements
from .ai.adaptive import get_weak_spots, get_user_strengths
from .ai.openai_client import openai_client, generate_study_recommendations
from .ui.components import PracticeQuestionView
from .utils.helpers import create_progress_bar, create_clean_stats_table, get_rank_display, get_skill_tier

# Import configuration
from config import (
    COMPTIA_CERTS, CYBER_QUOTES, DISCORD_TOKEN, OPENAI_API_KEY,
    validate_question_count, format_study_domains_list
)

# Bot Configuration
intents = discord.Intents.default()
intents.message_content = True
study_bot = commands.Bot(command_prefix='!', intents=intents)

# Global storage for active sessions and user data
user_study_data = {}  # Legacy fallback - main storage now in database
user_flashcard_collections = {}  # Flashcard storage
pomodoro_sessions = {}  # Active Pomodoro timers

# ═══════════════════════════════════════════════════════════════════════════════════
# BOT EVENT HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════════

@study_bot.event
async def on_ready():
    """Event handler for when bot successfully connects to Discord"""
    print(f"🚀 Sentinel AI Study Bot is online as {study_bot.user}")
    print(f"   📊 Connected to {len(study_bot.guilds)} Discord servers")
    print(f"   👥 Serving {len(set(study_bot.get_all_members()))} total users")
    
    # Set custom "Playing" status with creator credit
    activity = discord.Activity(type=discord.ActivityType.playing, name="/help — Created by Yorouki")
    await study_bot.change_presence(activity=activity)
    print(f"   🎯 Status set: Playing /help — Created by Yorouki")
    
    # Start the heartbeat task
    study_bot.loop.create_task(daily_heartbeat_task())

@study_bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handle slash command errors gracefully"""
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"Command is on cooldown. Try again in {error.retry_after:.2f} seconds.", ephemeral=True)
    else:
        await interaction.response.send_message("An error occurred while processing your request.", ephemeral=True)
        print(f"❌ Command error: {error}")

# ═══════════════════════════════════════════════════════════════════════════════════
# SETUP AND INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════════

@study_bot.event
async def setup_hook():
    """Initialize bot components and sync commands"""
    # Initialize database schema
    if initialize_database():
        print("✅ Database schema ready for persistent user progress")
    else:
        print("⚠️ Database initialization failed, using fallback in-memory storage")
    
    # Sync slash commands
    try:
        synced = await study_bot.tree.sync()
        print(f"✅ Successfully synced {len(synced)} slash commands")
        for command in synced:
            print(f"   📝 Registered command: /{command.name}")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

async def daily_heartbeat_task():
    """Send daily motivational messages"""
    await study_bot.wait_until_ready()
    print("💓 Daily heartbeat task started")
    
    while not study_bot.is_closed():
        try:
            # Send a daily message (you can customize this)
            for guild in study_bot.guilds:
                # Find a general channel to send heartbeat
                for channel in guild.text_channels:
                    if channel.name in ['general', 'bot-commands', 'study']:
                        heartbeat_message = "💓 Daily CompTIA study reminder: Stay consistent and you'll succeed!"
                        await channel.send(heartbeat_message)
                        print("💓 Daily heartbeat message sent successfully")
                        break
                break  # Only send to first guild
            
        except Exception as e:
            print(f"❌ Heartbeat error: {e}")
        
        # Wait 24 hours before next heartbeat
        await asyncio.sleep(24 * 60 * 60)

# ═══════════════════════════════════════════════════════════════════════════════════
# STUDY MANAGEMENT COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════════

@study_bot.tree.command(name="certs", description="View available CompTIA certifications")
async def display_certifications(interaction: discord.Interaction):
    """Display all available CompTIA certifications with descriptions."""
    certifications_embed = discord.Embed(
        title="CompTIA Certifications",
        description="*Professional certification paths for cybersecurity and IT excellence*",
        color=0x2B2D31
    )
    
    # Add certifications in clean format
    for cert_code, cert_details in COMPTIA_CERTS.items():
        cert_emoji = {"A+": "🖥️", "Security+": "🔒", "Network+": "🌐", "CySA+": "🛡️"}.get(cert_code, "📜")
        
        certifications_embed.add_field(
            name=f"{cert_emoji} {cert_code}",
            value=f"{cert_details['name']}",
            inline=True
        )
    
    certifications_embed.set_footer(text="Use /selectcert to choose your track")
    await interaction.response.send_message(embed=certifications_embed)
    print(f"📚 User {interaction.user.name} viewed available certifications")

@study_bot.tree.command(name="selectcert", description="Select a CompTIA certification to study for")
@app_commands.describe(certification="Choose your CompTIA certification")
@app_commands.choices(certification=[
    app_commands.Choice(name="CompTIA A+", value="A+"),
    app_commands.Choice(name="CompTIA Security+", value="Security+"),
    app_commands.Choice(name="CompTIA Network+", value="Network+"),
    app_commands.Choice(name="CompTIA CySA+", value="CySA+"),
])
async def select_certification_focus(interaction: discord.Interaction, certification: str):
    """Let users select their CompTIA certification focus."""
    user_discord_id = interaction.user.id
    
    # Get or create user data from database
    user_data = await get_user_data(user_discord_id, str(interaction.user.name))
    
    # Set their selected certification
    user_data["selected_cert"] = certification
    
    # Save to database
    await update_user_data(user_discord_id, user_data)
    
    # Get certification details from config
    selected_cert_info = COMPTIA_CERTS[certification]
    
    # Create clean confirmation embed
    cert_emoji = {"A+": "🖥️", "Security+": "🔒", "Network+": "🌐", "CySA+": "🛡️"}.get(certification, "📜")
    
    selection_embed = discord.Embed(
        title=f"Certification Selected • {certification}",
        description=f"*Now focused on {selected_cert_info['name']}*",
        color=0x2B2D31
    )
    
    # Study domains
    domains_formatted = '\n'.join([f"• {domain}" for domain in selected_cert_info['domains']])
    selection_embed.add_field(
        name=f"{cert_emoji} Study Domains", 
        value=domains_formatted, 
        inline=False
    )
    
    # Next steps
    selection_embed.add_field(
        name="🚀 Ready to Begin", 
        value="`/practice` Practice questions\n"
              "`/pomodoro` Study sessions\n"
              "`/flashcards` Create cards", 
        inline=False
    )
    
    await interaction.response.send_message(embed=selection_embed)
    print(f"🎯 User {interaction.user.name} selected {certification} certification")

@study_bot.tree.command(name="studystats", description="View your comprehensive study progress and statistics")
async def display_study_statistics(interaction: discord.Interaction):
    """Show users their study progress, statistics, and achievements."""
    user_discord_id = interaction.user.id
    
    # Get user data from database
    user_data = await get_user_data(user_discord_id, str(interaction.user.name))
    
    # Check if user has selected a certification yet
    if not user_data.get("selected_cert"):
        await interaction.response.send_message(
            "📊 No study data found. Start studying with `/selectcert` to track your progress!", 
            ephemeral=True
        )
        return
    
    # Create clean statistics embed
    cert = user_data.get('selected_cert', 'No Certification Selected')
    stats_embed = discord.Embed(
        title=f"Study Progress • {cert}",
        description="*Real-time analytics and performance tracking*",
        color=0x2B2D31
    )
    
    # Core metrics
    total_questions = user_data.get('total_questions', 0)
    correct_answers = user_data.get('correct_answers', 0)
    total_minutes = user_data.get('study_time_minutes', 0)
    study_score = user_data.get('study_score', 0)
    study_streak = user_data.get('study_streak', 0)
    
    if total_questions > 0:
        accuracy_rate = (correct_answers / total_questions) * 100
        accuracy_bar = create_progress_bar(correct_answers, total_questions)
        
        stats_embed.add_field(
            name="📊 Performance Overview",
            value=f"Questions Answered: {total_questions}\n"
                  f"Correct Answers: {correct_answers}\n"
                  f"Study Score: {study_score}",
            inline=True
        )
        
        stats_embed.add_field(
            name="📈 Overall Accuracy",
            value=accuracy_bar,
            inline=False
        )
    else:
        stats_embed.add_field(
            name="📊 Performance Overview",
            value="No practice data yet\nStart with `/practice` to track progress",
            inline=False
        )
    
    # Additional metrics
    stats_embed.add_field(
        name="🔥 Study Streak",
        value=f"{study_streak} days",
        inline=True
    )
    
    stats_embed.add_field(
        name="⏱️ Study Time", 
        value=f"{total_minutes} minutes",
        inline=True
    )
    
    if user_discord_id in user_flashcard_collections and user_flashcard_collections[user_discord_id]:
        flashcard_count = len(user_flashcard_collections[user_discord_id])
        stats_embed.add_field(
            name="🗃️ Flashcards",
            value=f"{flashcard_count} created",
            inline=True
        )
    
    stats_embed.set_footer(text="Live tracking • Use /analysis for AI insights")
    await interaction.response.send_message(embed=stats_embed)
    print(f"📊 User {interaction.user.name} viewed their study statistics")

# ═══════════════════════════════════════════════════════════════════════════════════
# AI-POWERED STUDY COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════════

@study_bot.tree.command(name="practice", description="Generate AI-powered practice questions for your certification")
@app_commands.describe(
    difficulty="Choose question difficulty level", 
    count="Number of questions to generate (1-5)"
)
@app_commands.choices(difficulty=[
    app_commands.Choice(name="Beginner", value="beginner"),
    app_commands.Choice(name="Intermediate", value="intermediate"),
    app_commands.Choice(name="Advanced", value="advanced"),
])
async def generate_practice_questions(interaction: discord.Interaction, difficulty: str = "intermediate", count: int = 1):
    """Generate AI-powered practice questions using OpenAI."""
    user_discord_id = interaction.user.id
    
    # Get user data from database
    user_data = await get_user_data(user_discord_id, str(interaction.user.name))
    
    # Validate user has selected a certification
    if not user_data.get("selected_cert"):
        await interaction.response.send_message(
            "❌ Please select a certification first using `/selectcert`!", 
            ephemeral=True
        )
        return
    
    # Check if OpenAI is available
    if not openai_client:
        await interaction.response.send_message(
            "❌ AI features are currently unavailable. Please check the OpenAI API configuration.", 
            ephemeral=True
        )
        return
    
    # Validate and clamp question count
    validated_count = validate_question_count(count, max_allowed=5)
    
    # Get user's selected certification info
    user_certification = user_data["selected_cert"]
    cert_details = COMPTIA_CERTS[user_certification]
    
    # Check for new achievements
    new_achievements = await check_achievements(user_discord_id, user_certification)
    
    # Defer response since AI generation takes time
    await interaction.response.defer()
    
    try:
        # Create AI prompt for question generation
        focused_domains = ', '.join(cert_details['domains'][:3])
        
        ai_prompt = f"""Generate {validated_count} {difficulty}-level multiple choice practice question(s) for CompTIA {user_certification} certification.

For each question:
- Focus on domains: {focused_domains}
- Create 4 answer choices (A, B, C, D)
- Provide detailed explanations for correct answers
- Use realistic exam-style scenarios
- Include technical depth appropriate for {difficulty} level

Format as JSON array with objects containing:
- "question": "Question text"
- "options": {{"A": "option text", "B": "option text", "C": "option text", "D": "option text"}}
- "answer": "A" (correct letter)
- "explanation": "Detailed explanation of why this is correct"

Return valid JSON only."""
        
        # Generate questions using OpenAI
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert CompTIA certification instructor creating practice questions."},
                {"role": "user", "content": ai_prompt}
            ],
            max_tokens=2000,
            temperature=0.7
        )
        
        # Parse the AI response
        ai_response = response.choices[0].message.content
        if ai_response is None:
            raise ValueError("OpenAI returned empty response")
        ai_response = ai_response.strip()
        
        # Clean up response to ensure valid JSON
        if ai_response.startswith("```json"):
            ai_response = ai_response[7:-3]
        elif ai_response.startswith("```"):
            ai_response = ai_response[3:-3]
        
        # Parse JSON response
        parsed_questions = json.loads(ai_response)
        
        # Ensure it's a list
        if not isinstance(parsed_questions, list):
            parsed_questions = [parsed_questions]
        
        # Validate we got the right number of questions
        if len(parsed_questions) != validated_count:
            raise ValueError(f"Expected {validated_count} questions, got {len(parsed_questions)}")
        
        # Create success message
        print(f"🤖 Generating {validated_count} {difficulty} questions for {user_certification}")
        await interaction.followup.send(f"🤖 Generated {validated_count} {difficulty} practice questions for {user_certification}! Get ready...")
        
        # Brief pause for dramatic effect
        await asyncio.sleep(1)
        
        # Send only the first question initially
        first_question = parsed_questions[0]
        remaining_questions = parsed_questions[1:] if len(parsed_questions) > 1 else []
        
        # Create first question embed
        first_question_embed = discord.Embed(
            title=f"Practice Question 1/{len(parsed_questions)} • {user_certification} ({difficulty.title()})",
            description=f"*{first_question['question']}*",
            color=0x2B2D31
        )
        
        # Add the multiple choice options to the embed
        if 'options' in first_question:
            options_text = ""
            for letter, option in first_question['options'].items():
                options_text += f"**{letter.upper()})** {option}\n"
            first_question_embed.add_field(
                name="Answer Choices",
                value=options_text,
                inline=False
            )
        
        first_question_embed.set_footer(text="⏰ Time remaining: 60 seconds - Click a button to answer!")
        
        # Create interactive view with buttons for first question
        first_question_view = PracticeQuestionView(
            correct_answer=first_question['answer'],
            explanation=first_question['explanation'], 
            user_id=user_discord_id,
            question_number=1,
            total_questions=len(parsed_questions),
            remaining_questions=remaining_questions,
            interaction_context=interaction,
            question_text=first_question['question'],
            certification=user_certification
        )
        
        # Send first question with interactive buttons
        first_message = await interaction.followup.send(embed=first_question_embed, view=first_question_view)
        await first_question_view.start_countdown(first_message)
        
        # Update user's question count for statistics
        user_data["total_questions"] += validated_count
        await update_user_data(user_discord_id, user_data)
        
        # Show achievement notifications if any
        if new_achievements:
            for achievement in new_achievements:
                achievement_embed = discord.Embed(
                    title="Achievement Unlocked!",
                    description=f"**{achievement['name']}**\n{achievement['description']}",
                    color=0xffd700
                )
                achievement_embed.add_field(name="Points Earned", value=f"{achievement['points']} pts", inline=True)
                await interaction.followup.send(embed=achievement_embed)
        
        print(f"✅ Generated {validated_count} questions for {interaction.user.name}")
        
    except Exception as generation_error:
        error_message = f"❌ Error generating questions: {str(generation_error)}"
        await interaction.followup.send(error_message, ephemeral=True)
        print(f"❌ Question generation failed: {generation_error}")

# ═══════════════════════════════════════════════════════════════════════════════════
# PROFESSIONAL LEADERBOARDS
# ═══════════════════════════════════════════════════════════════════════════════════

@study_bot.tree.command(name="leaderboard", description="View competitive study leaderboards and rankings")
async def show_leaderboard(interaction: discord.Interaction):
    """Display comprehensive study leaderboards with multiple ranking categories."""
    await interaction.response.defer()
    
    try:
        # Get all leaderboard data
        daily_champs = await get_daily_champions()
        accuracy_masters = await get_accuracy_masters()
        study_legends = await get_study_legends()
        
        # Create main leaderboard embed - Futuristic Design
        leaderboard_embed = discord.Embed(
            title="Study Leaderboards",
            description="*Real-time performance rankings across all CompTIA certifications*",
            color=0x2B2D31
        )
        
        # Daily Champions Section - Modern Format
        if daily_champs:
            daily_text = "```ansi\n\u001b[37m\u001b[1mRank  Player            Questions\u001b[0m\n"
            daily_text += "─" * 32 + "\n"
            for i, champ in enumerate(daily_champs, 1):
                daily_text += f"\u001b[32m{i:2}.\u001b[0m   {champ['username']:<15} {champ['questions_today']:>3}\n"
            daily_text += "```"
            leaderboard_embed.add_field(
                name="🏆 **Daily Champions**",
                value=daily_text,
                inline=True
            )
        else:
            leaderboard_embed.add_field(
                name="🏆 **Daily Champions**", 
                value="*No activity recorded today*\nBe the first to practice!",
                inline=True
            )
        
        # Accuracy Masters Section - Sleek Format
        if accuracy_masters:
            accuracy_text = "```ansi\n\u001b[37m\u001b[1mRank  Player            Accuracy\u001b[0m\n"
            accuracy_text += "─" * 32 + "\n"
            for i, master in enumerate(accuracy_masters, 1):
                color = "\u001b[32m" if master['accuracy'] >= 80 else "\u001b[33m" if master['accuracy'] >= 60 else "\u001b[31m"
                accuracy_text += f"{color}{i:2}.\u001b[0m   {master['username']:<15} {color}{master['accuracy']:>5.1f}%\u001b[0m\n"
            accuracy_text += "```"
            leaderboard_embed.add_field(
                name="🎯 **Accuracy Masters**",
                value=accuracy_text,
                inline=True
            )
        else:
            leaderboard_embed.add_field(
                name="🎯 **Accuracy Masters**",
                value="*Minimum 10 questions required*\nStart practicing to appear here!",
                inline=True
            )
        
        # Study Legends Section - Futuristic Design
        if study_legends:
            legends_text = "```ansi\n\u001b[37m\u001b[1mRank  Player             Score     Questions\u001b[0m\n"
            legends_text += "─" * 42 + "\n"
            for i, legend in enumerate(study_legends, 1):
                rank_color = "\u001b[33m" if i <= 3 else "\u001b[36m" if i <= 5 else "\u001b[37m"
                score_color = "\u001b[32m" if legend['study_score'] > 0 else "\u001b[31m"
                legends_text += f"{rank_color}{i:2}.\u001b[0m   {legend['username']:<15} {score_color}{legend['study_score']:>6}\u001b[0m     {legend['total_questions']:>6}\n"
            legends_text += "```"
            leaderboard_embed.add_field(
                name="👑 **Study Legends**",
                value=legends_text,
                inline=False
            )
        else:
            leaderboard_embed.add_field(
                name="👑 **Study Legends**",
                value="*The leaderboard awaits your excellence*\nStart your journey with `/practice`",
                inline=False
            )
        
        leaderboard_embed.set_footer(text="⚡ Live Rankings • Climb the leaderboard with /practice")
        
        await interaction.followup.send(embed=leaderboard_embed)
        print(f"🏆 {interaction.user.name} viewed the leaderboards")
        
    except Exception as e:
        error_embed = discord.Embed(
            title="Leaderboard Error",
            description="Sorry, I couldn't load the leaderboards right now. Please try again!",
            color=0xff4444
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)
        print(f"❌ Leaderboard error: {e}")

# ═══════════════════════════════════════════════════════════════════════════════════  
# AI ANALYSIS DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════════

@study_bot.tree.command(name="analysis", description="View your personalized AI-powered study analysis and insights")
async def show_study_analysis(interaction: discord.Interaction):
    """Display comprehensive AI-powered study analysis with beautiful professional UI"""
    await interaction.response.defer()
    
    user_discord_id = interaction.user.id
    user_data = await get_user_data(user_discord_id, str(interaction.user.name))
    
    if not user_data.get("selected_cert"):
        error_embed = discord.Embed(
            title="Analysis Unavailable",
            description="Please select a certification first using `/selectcert`",
            color=0xff6b6b
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)
        return
    
    certification = user_data["selected_cert"]
    
    try:
        # Get comprehensive data
        weak_spots = await get_weak_spots(user_discord_id, certification, 5)
        strengths = await get_user_strengths(user_discord_id, certification, 3)
        
        # Create clean analysis embed
        analysis_embed = discord.Embed(
            title=f"Study Analysis • {certification}",
            description="*AI-powered insights and personalized recommendations for exam success*",
            color=0x2B2D31
        )
        
        # Performance Overview
        if user_data['total_questions'] > 0:
            accuracy = (user_data['correct_answers'] / user_data['total_questions']) * 100
            performance_bar = create_progress_bar(user_data['correct_answers'], user_data['total_questions'])
            
            analysis_embed.add_field(
                name="📊 Performance Overview",
                value=f"Questions Answered: {user_data['total_questions']}\n"
                      f"Correct Answers: {user_data['correct_answers']}\n"
                      f"Study Score: {user_data['study_score']}",
                inline=False
            )
            
            analysis_embed.add_field(
                name="Overall Accuracy",
                value=performance_bar,
                inline=False
            )
        else:
            analysis_embed.add_field(
                name="📊 Performance Overview", 
                value="No practice data yet\nStart with `/practice` to see your metrics",
                inline=False
            )
        
        # Weak Spots Analysis - Clean Professional Format
        if weak_spots:
            weak_data = [(spot['topic'], spot['accuracy'], spot['questions_attempted']) for spot in weak_spots]
            weak_table = create_clean_stats_table(weak_data)
            
            analysis_embed.add_field(
                name="⚠️ Areas for Improvement",
                value=weak_table,
                inline=False
            )
        else:
            analysis_embed.add_field(
                name="⚠️ Areas for Improvement",
                value="Answer more questions to identify weaknesses and get targeted insights!",
                inline=False
            )
        
        # Strengths Section
        if strengths:
            strength_data = [(strength['topic'], strength['accuracy'], strength['questions_attempted']) for strength in strengths]
            strength_table = create_clean_stats_table(strength_data)
            
            analysis_embed.add_field(
                name="✅ Your Strengths", 
                value=strength_table,
                inline=False
            )
        
        # AI Recommendations
        recommendations = await generate_study_recommendations(user_discord_id, certification, weak_spots, strengths)
        if recommendations:
            analysis_embed.add_field(
                name="🤖 AI Study Recommendations",
                value=recommendations,
                inline=False
            )
        
        analysis_embed.set_footer(text="Analysis powered by adaptive AI • Updates in real-time as you study")
        
        await interaction.followup.send(embed=analysis_embed)
        print(f"🧠 {interaction.user.name} viewed their AI study analysis")
        
    except Exception as e:
        error_embed = discord.Embed(
            title="Analysis Error",
            description="Unable to generate study analysis. Please try again.",
            color=0xff6b6b
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)
        print(f"❌ Analysis error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════════
# HELP & INFORMATION COMMANDS  
# ═══════════════════════════════════════════════════════════════════════════════════

@study_bot.tree.command(name="help", description="View all available bot commands with detailed explanations")
async def show_help_menu(interaction: discord.Interaction):
    """Display comprehensive help menu with all bot commands."""
    help_embed = discord.Embed(
        title="Sentinel • AI Study Bot",
        description="*Professional AI-powered study platform for any subject*",
        color=0x2B2D31
    )
    
    # Study Management
    help_embed.add_field(
        name="📚 Study Management",
        value="`/certs` View certifications\n"
              "`/selectcert` Choose track\n" 
              "`/studystats` Progress dashboard",
        inline=True
    )
    
    # AI Tools
    help_embed.add_field(
        name="🧠 AI Study Tools",
        value="`/practice` Practice questions\n"
              "`/analysis` Study insights\n"
              "`/flashcards` Create cards\n"
              "`/explain` Get explanations",
        inline=True
    )
    
    # Productivity
    help_embed.add_field(
        name="🏆 Productivity",
        value="`/pomodoro` Study sessions\n"
              "`/leaderboard` Rankings\n"
              "`/stoppomodoro` End session",
        inline=True
    )
    
    # Security Tools
    help_embed.add_field(
        name="🔒 Security Tools",
        value="`/cyberquote` Wisdom\n"
              "`/scan` Port analysis\n"
              "`/hash` SHA-256 hash\n"
              "`/iplookup` IP lookup\n"
              "`/passwordcheck` Password analyzer",
        inline=True
    )
    
    # System
    help_embed.add_field(
        name="⚙️ System",
        value="`/ping` Bot status\n"
              "`/about` Bot info & credits",
        inline=True
    )
    
    help_embed.set_footer(text="Quick Start: /selectcert → /practice → /analysis")
    
    await interaction.response.send_message(embed=help_embed)
    print(f"❓ {interaction.user.name} viewed the help menu")

@study_bot.tree.command(name="about", description="View bot information, creator credits, and development details")
async def show_about_info(interaction: discord.Interaction):
    """Display bot information and creator credits."""
    about_embed = discord.Embed(
        title="About Sentinel AI Study Bot",
        description="*Professional AI-powered study assistant for Discord*",
        color=0x2B2D31
    )
    
    # Bot Information
    about_embed.add_field(
        name="🤖 **Bot Details**",
        value="**Name:** Sentinel AI Study Bot\n"
              "**Version:** 2.0.0\n"
              "**Features:** 17+ Commands\n"
              "**Status:** 100% Free",
        inline=True
    )
    
    # Creator Credits
    about_embed.add_field(
        name="👨‍💻 **Created By**",
        value="**Developer:** Yorouki\n"
              "**GitHub:** Coming Soon\n"
              "**Type:** Open Source Project\n"
              "**Year:** 2025",
        inline=True
    )
    
    # Technical Stack
    about_embed.add_field(
        name="⚡ **Technology**",
        value="**Language:** Python 3.11\n"
              "**AI:** OpenAI GPT-3.5\n"
              "**Framework:** Discord.py\n"
              "**Platform:** Replit",
        inline=True
    )
    
    # Key Features
    about_embed.add_field(
        name="✨ **Key Features**",
        value="• AI Practice Questions & Explanations\n"
              "• Smart Flashcard Generation\n"
              "• Adaptive Learning System\n"
              "• Cybersecurity Tools\n"
              "• Pomodoro Study Sessions\n"
              "• Progress Tracking & Analytics",
        inline=False
    )
    
    # Support Information
    about_embed.add_field(
        name="🛠️ **Support & Development**",
        value="Sentinel is actively maintained and updated regularly.\n"
              "All features are completely free to encourage learning!\n"
              "⭐ Star us on GitHub when released!",
        inline=False
    )
    
    about_embed.set_footer(text="Made with ❤️ by Yorouki • Powered by AI")
    
    await interaction.response.send_message(embed=about_embed)
    print(f"ℹ️ {interaction.user.name} viewed bot information")

# ═══════════════════════════════════════════════════════════════════════════════════
# AI LEARNING TOOLS (FLASHCARDS & EXPLANATIONS)
# ═══════════════════════════════════════════════════════════════════════════════════

@study_bot.tree.command(name="flashcards", description="Generate AI flashcards for CompTIA topics")
@app_commands.describe(topic="Specific topic to create flashcards for", count="Number of flashcards (1-10)")
async def create_ai_flashcards(interaction: discord.Interaction, topic: str = None, count: int = 3):
    """Generate AI-powered flashcards for study topics."""
    user_discord_id = interaction.user.id
    user_data = await get_user_data(user_discord_id, str(interaction.user.name))
    
    if not user_data.get("selected_cert"):
        await interaction.response.send_message(
            "❌ Please select a certification first using `/selectcert`!", 
            ephemeral=True
        )
        return
    
    if not openai_client:
        await interaction.response.send_message(
            "❌ AI features are currently unavailable. Please check the OpenAI API configuration.", 
            ephemeral=True
        )
        return
    
    # Validate count
    validated_count = max(1, min(count, 10))
    certification = user_data["selected_cert"]
    
    await interaction.response.defer()
    
    try:
        # Generate topic if not provided
        if not topic:
            cert_domains = COMPTIA_CERTS[certification]['domains']
            topic = random.choice(cert_domains)
        
        # Create AI prompt for flashcards
        prompt = f"""Create {validated_count} study flashcard(s) for CompTIA {certification} on the topic: {topic}

For each flashcard, provide:
- A clear, concise question or term
- A comprehensive answer with key details
- Make them exam-relevant and practical

Format as JSON array:
[{{"front": "Question/Term", "back": "Answer/Explanation"}}]

Focus on important concepts students need to memorize for the exam."""
        
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"You are a CompTIA {certification} instructor creating study flashcards."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.7
        )
        
        # Parse AI response
        ai_response = response.choices[0].message.content
        if ai_response is None:
            raise ValueError("OpenAI returned empty response")
        ai_response = ai_response.strip()
        if ai_response.startswith("```json"):
            ai_response = ai_response[7:-3]
        elif ai_response.startswith("```"):
            ai_response = ai_response[3:-3]
        
        flashcards = json.loads(ai_response)
        
        # Store flashcards for user
        if user_discord_id not in user_flashcard_collections:
            user_flashcard_collections[user_discord_id] = []
        
        user_flashcard_collections[user_discord_id].extend(flashcards)
        
        # Create clean flashcards embed
        flashcards_embed = discord.Embed(
            title=f"AI Flashcards • {topic}",
            description=f"*Generated {len(flashcards)} flashcards for {certification}*",
            color=0x2B2D31
        )
        
        # Show flashcards in clean format
        for i, card in enumerate(flashcards[:3], 1):
            flashcards_embed.add_field(
                name=f"📇 Card {i}", 
                value=f"Q: {card['front']}\nA: {card['back']}", 
                inline=True
            )
        
        if len(flashcards) > 3:
            flashcards_embed.add_field(
                name="Collection Update", 
                value=f"+{len(flashcards) - 3} more cards saved", 
                inline=False
            )
        
        flashcards_embed.set_footer(text=f"Total: {len(user_flashcard_collections[user_discord_id])} flashcards")
        
        await interaction.followup.send(embed=flashcards_embed)
        print(f"🗃️ Generated {len(flashcards)} flashcards for {interaction.user.name} on {topic}")
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error generating flashcards: {str(e)}", ephemeral=True)
        print(f"❌ Flashcard generation error: {e}")

@study_bot.tree.command(name="explain", description="Get detailed AI explanations of any study topic")
@app_commands.describe(topic="Topic or concept you want explained")
async def explain_topic(interaction: discord.Interaction, topic: str):
    """Provide detailed AI explanations of any study topic."""
    user_discord_id = interaction.user.id
    user_data = await get_user_data(user_discord_id, str(interaction.user.name))
    
    if not user_data.get("selected_cert"):
        await interaction.response.send_message(
            "❌ Please select a certification first using `/selectcert`!", 
            ephemeral=True
        )
        return
    
    if not openai_client:
        await interaction.response.send_message(
            "❌ AI features are currently unavailable.", 
            ephemeral=True
        )
        return
    
    certification = user_data["selected_cert"]
    await interaction.response.defer()
    
    try:
        prompt = f"""Explain this CompTIA {certification} topic in detail: {topic}

Provide:
- Clear definition and overview
- Key concepts and components  
- Real-world applications
- Common exam questions about this topic
- Important details students should memorize

Make it educational and exam-focused."""
        
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"You are an expert CompTIA {certification} instructor."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.3
        )
        
        explanation = response.choices[0].message.content
        if explanation is None:
            raise ValueError("OpenAI returned empty explanation")
        explanation = explanation.strip()
        
        # Create clean explanation embed
        explain_embed = discord.Embed(
            title=f"{certification} • {topic}",
            description=f"*AI-powered explanation*\n\n{explanation}",
            color=0x2B2D31
        )
        
        explain_embed.set_footer(text=f"Powered by AI • {certification} focused")
        
        await interaction.followup.send(embed=explain_embed)
        print(f"📖 Explained {topic} for {interaction.user.name}")
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error generating explanation: {str(e)}", ephemeral=True)
        print(f"❌ Explanation error: {e}")

# ═══════════════════════════════════════════════════════════════════════════════════
# POMODORO PRODUCTIVITY SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════════

@study_bot.tree.command(name="pomodoro", description="Start a focused study session with Pomodoro timer")
@app_commands.describe(session_type="Type of Pomodoro session to start")
@app_commands.choices(session_type=[
    app_commands.Choice(name="Study Session (25 min)", value="study"),
    app_commands.Choice(name="Short Break (5 min)", value="short_break"),
    app_commands.Choice(name="Long Break (15 min)", value="long_break"),
])
async def start_pomodoro_session(interaction: discord.Interaction, session_type: str = "study"):
    """Start a Pomodoro timer session for focused study."""
    user_discord_id = interaction.user.id
    
    # Check if user already has active session
    if user_discord_id in pomodoro_sessions:
        active_session = pomodoro_sessions[user_discord_id]
        remaining_time = active_session['end_time'] - datetime.utcnow()
        
        if remaining_time.total_seconds() > 0:
            await interaction.response.send_message(
                f"⏰ You already have an active {active_session['type']} session! "
                f"Time remaining: {int(remaining_time.total_seconds() / 60)} minutes. "
                f"Use `/stoppomodoro` to end it early.",
                ephemeral=True
            )
            return
    
    # Set session duration based on type
    durations = {
        "study": 25,
        "short_break": 5, 
        "long_break": 15
    }
    
    duration_minutes = durations.get(session_type, 25)
    end_time = datetime.utcnow() + timedelta(minutes=duration_minutes)
    
    # Store session data
    pomodoro_sessions[user_discord_id] = {
        "type": session_type,
        "start_time": datetime.utcnow(),
        "end_time": end_time,
        "duration": duration_minutes
    }
    
    # Create clean session embed
    session_emoji = "📚" if session_type == "study" else "☕"
    
    session_embed = discord.Embed(
        title=f"{session_emoji} Pomodoro {session_type.replace('_', ' ').title()}",
        description=f"*{duration_minutes}-minute focused session active*",
        color=0x2B2D31
    )
    
    session_embed.add_field(
        name="⏱️ Session Info",
        value=f"Duration: {duration_minutes} minutes\n"
              f"Ends: <t:{int(end_time.timestamp())}:t>\n"
              f"Status: 🟢 Active",
        inline=True
    )
    
    if session_type == "study":
        session_embed.add_field(
            name="💡 Study Tips",
            value="• Focus on CompTIA materials\n"
                  "• Use `/practice` actively\n"
                  "• Note weak areas",
            inline=True
        )
    else:
        session_embed.add_field(
            name="🧘 Break Tips",
            value="• Step away from screen\n"
                  "• Stretch and move\n"
                  "• Hydrate well",
            inline=True
        )
    
    session_embed.set_footer(text="Use /stoppomodoro to end early")
    
    await interaction.response.send_message(embed=session_embed)
    print(f"⏰ {interaction.user.name} started {session_type} Pomodoro session")
    
    # Schedule completion notification
    study_bot.loop.create_task(pomodoro_completion_task(interaction, user_discord_id, session_type, duration_minutes))

async def pomodoro_completion_task(interaction, user_id, session_type, duration_minutes):
    """Handle Pomodoro session completion."""
    await asyncio.sleep(duration_minutes * 60)  # Convert to seconds
    
    # Check if session is still active (not manually stopped)
    if user_id in pomodoro_sessions:
        # Remove completed session
        del pomodoro_sessions[user_id]
        
        # Create completion embed
        completion_embed = discord.Embed(
            title="🎉 Pomodoro Session Complete!",
            description=f"Your {session_type.replace('_', ' ')} session ({duration_minutes} min) is finished!",
            color=0x00ff00
        )
        
        if session_type == "study":
            completion_embed.add_field(
                name="Great Job!",
                value="Time for a break! Use `/pomodoro short_break` to start a 5-minute break.",
                inline=False
            )
            
            # Update study time in user data
            user_data = await get_user_data(user_id)
            user_data["study_time_minutes"] += duration_minutes
            await update_user_data(user_id, user_data)
        else:
            completion_embed.add_field(
                name="Break Complete!",
                value="Ready to get back to studying? Use `/pomodoro study` for another focused session.",
                inline=False
            )
        
        try:
            await interaction.followup.send(embed=completion_embed)
        except:
            # If followup fails, try to send a new message to the channel
            try:
                await interaction.channel.send(f"🎉 <@{user_id}> Your Pomodoro session is complete!", embed=completion_embed)
            except:
                pass

@study_bot.tree.command(name="stoppomodoro", description="Stop your current Pomodoro session")
async def stop_pomodoro_session(interaction: discord.Interaction):
    """Stop the user's active Pomodoro session."""
    user_discord_id = interaction.user.id
    
    if user_discord_id not in pomodoro_sessions:
        await interaction.response.send_message("❌ You don't have an active Pomodoro session!", ephemeral=True)
        return
    
    session = pomodoro_sessions[user_discord_id]
    elapsed_time = datetime.utcnow() - session['start_time']
    elapsed_minutes = int(elapsed_time.total_seconds() / 60)
    
    # Remove session
    del pomodoro_sessions[user_discord_id]
    
    # Create stop confirmation embed
    stop_embed = discord.Embed(
        title="⏹️ Pomodoro Session Stopped",
        description=f"Your {session['type'].replace('_', ' ')} session has been ended early.",
        color=0xff6b6b
    )
    
    stop_embed.add_field(
        name="Session Summary",
        value=f"Planned duration: {session['duration']} minutes\n"
              f"Actual time: {elapsed_minutes} minutes",
        inline=True
    )
    
    # Update study time if it was a study session
    if session['type'] == "study" and elapsed_minutes > 0:
        user_data = await get_user_data(user_discord_id)
        user_data["study_time_minutes"] += elapsed_minutes
        await update_user_data(user_discord_id, user_data)
        
        stop_embed.add_field(
            name="Study Time Added",
            value=f"{elapsed_minutes} minutes added to your total study time",
            inline=True
        )
    
    await interaction.response.send_message(embed=stop_embed)
    print(f"⏹️ {interaction.user.name} stopped Pomodoro session after {elapsed_minutes} minutes")

# ═══════════════════════════════════════════════════════════════════════════════════
# LEGACY CYBERSECURITY TOOLS 
# ═══════════════════════════════════════════════════════════════════════════════════

@study_bot.tree.command(name="cyberquote", description="Get inspirational cybersecurity quotes for motivation")
async def send_cybersecurity_quote(interaction: discord.Interaction):
    """Send a motivational cybersecurity quote."""
    quote = random.choice(CYBER_QUOTES)
    
    quote_embed = discord.Embed(
        title="Cybersecurity Wisdom",
        description=f"*Professional insights from industry leaders*\n\n**\"{quote}\"**",
        color=0x2B2D31
    )
    
    quote_embed.set_footer(text="🔒 Stay motivated • Security is a mindset, not a destination")
    
    await interaction.response.send_message(embed=quote_embed)
    print(f"💡 Sent cybersecurity quote to {interaction.user.name}")

@study_bot.tree.command(name="scan", description="Scan a host and port for network security analysis")
@app_commands.describe(host="Target host/IP address to scan", port="Port number to check")
async def network_port_scan(interaction: discord.Interaction, host: str, port: int):
    """Perform a basic port scan on specified host and port."""
    await interaction.response.defer()
    
    try:
        # Validate port range
        if not (1 <= port <= 65535):
            await interaction.followup.send("❌ Port must be between 1 and 65535!", ephemeral=True)
            return
        
        # Perform port scan
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        
        result = sock.connect_ex((host, port))
        sock.close()
        
        # Create scan result embed
        if result == 0:
            status = "OPEN"
            color = 0x00ff00
            status_icon = "✅"
        else:
            status = "CLOSED/FILTERED"
            color = 0xff4444
            status_icon = "❌"
        
        scan_embed = discord.Embed(
            title="Network Port Analysis",
            description=f"*TCP connection test results for security assessment*",
            color=0x2B2D31
        )
        
        scan_embed.add_field(
            name="🎯 **Target Information**",
            value=f"**Host:** `{host}`\n**Port:** `{port}`\n**Status:** {status_icon} **{status}**",
            inline=True
        )
        
        scan_embed.add_field(
            name="⚙️ **Scan Configuration**",
            value=f"**Protocol:** TCP\n**Timeout:** 3 seconds\n**Method:** Socket connect",
            inline=True
        )
        
        scan_embed.set_footer(text="⚠️ Ethical Use Only • Only scan authorized targets")
        
        await interaction.followup.send(embed=scan_embed)
        print(f"🔍 {interaction.user.name} scanned {host}:{port} - {status}")
        
    except Exception as e:
        await interaction.followup.send(f"❌ Scan failed: {str(e)}", ephemeral=True)
        print(f"❌ Port scan error: {e}")

@study_bot.tree.command(name="hash", description="Generate SHA-256 hash of input text")
@app_commands.describe(text="Text to hash using SHA-256")
async def generate_hash(interaction: discord.Interaction, text: str):
    """Generate SHA-256 hash of provided text."""
    try:
        # Generate SHA-256 hash
        hash_object = hashlib.sha256(text.encode())
        hex_hash = hash_object.hexdigest()
        
        # Create modern hash result embed
        hash_embed = discord.Embed(
            title="SHA-256 Hash Generator",
            description="*Cryptographic hash function for data integrity verification*",
            color=0x2B2D31
        )
        
        input_preview = text[:100] + '...' if len(text) > 100 else text
        hash_embed.add_field(
            name="📝 **Input Text**", 
            value=f"```\n{input_preview}\n```", 
            inline=False
        )
        hash_embed.add_field(
            name="🔐 **SHA-256 Hash**", 
            value=f"```\n{hex_hash}\n```", 
            inline=False
        )
        
        hash_embed.set_footer(text="🔒 Secure • Industry-standard SHA-256 algorithm")
        
        await interaction.response.send_message(embed=hash_embed)
        print(f"🔒 Generated hash for {interaction.user.name}")
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Hash generation failed: {str(e)}", ephemeral=True)
        print(f"❌ Hash generation error: {e}")

@study_bot.tree.command(name="iplookup", description="Look up geographic and ISP information for an IP address")
@app_commands.describe(ip="IP address to lookup")
async def lookup_ip_info(interaction: discord.Interaction, ip: str):
    """Look up information about an IP address."""
    await interaction.response.defer()
    
    try:
        # Validate IP format (basic check)
        if not re.match(r'^(\d{1,3}\.){3}\d{1,3}$', ip):
            await interaction.followup.send("❌ Invalid IP address format!", ephemeral=True)
            return
        
        # Use ipapi.co for IP lookup
        response = requests.get(f"https://ipapi.co/{ip}/json/", timeout=5)
        data = response.json()
        
        if 'error' in data:
            await interaction.followup.send(f"❌ IP lookup failed: {data['reason']}", ephemeral=True)
            return
        
        # Create modern IP info embed
        ip_embed = discord.Embed(
            title=f"IP Geolocation Analysis",
            description=f"*Geographic and network information for `{ip}`*",
            color=0x2B2D31
        )
        
        # Location information
        location = f"{data.get('city', 'Unknown')}, {data.get('region', 'Unknown')}\n{data.get('country_name', 'Unknown')} ({data.get('country_code', 'N/A')})"
        ip_embed.add_field(
            name="🌍 **Geographic Location**", 
            value=location, 
            inline=True
        )
        
        # Network information
        network_info = f"**ISP:** {data.get('org', 'Unknown')}\n**Timezone:** {data.get('timezone', 'Unknown')}"
        if data.get('latitude') and data.get('longitude'):
            network_info += f"\n**Coordinates:** {data['latitude']}, {data['longitude']}"
        
        ip_embed.add_field(
            name="🌐 **Network Information**", 
            value=network_info, 
            inline=True
        )
        
        ip_embed.set_footer(text="📍 Powered by ipapi.co • Educational use only")
        
        await interaction.followup.send(embed=ip_embed)
        print(f"🌍 IP lookup for {ip} by {interaction.user.name}")
        
    except Exception as e:
        await interaction.followup.send(f"❌ IP lookup failed: {str(e)}", ephemeral=True)
        print(f"❌ IP lookup error: {e}")

@study_bot.tree.command(name="passwordcheck", description="Analyze password strength and time to crack scenarios")
@app_commands.describe(password="Password to analyze (hidden from other users)")
async def analyze_password_strength(interaction: discord.Interaction, password: str):
    """Analyze password strength with time-to-crack scenarios."""
    await interaction.response.defer(ephemeral=True)
    
    def calculate_entropy(pwd):
        """Calculate password entropy based on character set"""
        import string
        
        char_sets = [
            (string.ascii_lowercase, "lowercase letters"),
            (string.ascii_uppercase, "uppercase letters"), 
            (string.digits, "digits"),
            ("!@#$%^&*()_+-=[]{}|;:,.<>?", "special characters"),
            (" ", "spaces")
        ]
        
        char_space = 0
        used_sets = []
        
        for char_set, name in char_sets:
            if any(c in char_set for c in pwd):
                char_space += len(char_set)
                used_sets.append(name)
        
        if char_space == 0:
            return 0, []
        
        entropy = len(pwd) * math.log2(char_space)
        return entropy, used_sets
    
    def get_time_to_crack(entropy):
        """Calculate time to crack under different scenarios"""
        if entropy <= 0:
            return {}
        
        scenarios = {
            "amateur": {"speed": 1e3, "name": "Amateur Hacker", "icon": "💻"},
            "professional": {"speed": 1e6, "name": "Professional Hacker", "icon": "🎮"}, 
            "hacker_group": {"speed": 1e9, "name": "Hacker Group", "icon": "⚡"},
            "government": {"speed": 1e12, "name": "Government Agency", "icon": "🏛️"}
        }
        
        results = {}
        
        for scenario_id, scenario in scenarios.items():
            # Use logarithmic approach to avoid overflow
            log_combinations = entropy * math.log(2)  # log of 2^entropy
            log_speed = math.log(scenario["speed"])
            
            # Calculate log of seconds to crack (average = total/2)
            log_seconds = log_combinations - math.log(2) - log_speed
            
            # Convert back to actual time
            try:
                if log_seconds > 50:  # Very large number
                    seconds = float('inf')
                else:
                    seconds = math.exp(log_seconds)
            except OverflowError:
                seconds = float('inf')
                
            results[scenario_id] = {
                "name": scenario["name"],
                "icon": scenario["icon"], 
                "time": format_time_duration(seconds)
            }
        
        return results
    
    def format_time_duration(seconds):
        """Format seconds into human-readable duration"""
        if seconds == float('inf'):
            return "Longer than the age of the universe"
        elif seconds < 1:
            return "Less than 1 second"
        elif seconds < 60:
            return f"{seconds:.1f} seconds"
        elif seconds < 3600:
            return f"{seconds/60:.1f} minutes"  
        elif seconds < 86400:
            return f"{seconds/3600:.1f} hours"
        elif seconds < 31536000:
            return f"{seconds/86400:.1f} days"
        elif seconds < 31536000000:
            return f"{seconds/31536000:.1f} years"
        else:
            return f"{seconds/31536000:.0e} years"
    
    def get_strength_info(entropy):
        """Get strength level and score from entropy"""
        if entropy <= 0:
            return 0, "Very Weak", "🔴"
        elif entropy <= 30:
            return int((entropy / 30) * 25), "Very Weak", "🔴"
        elif entropy <= 50:
            return int(25 + ((entropy - 30) / 20) * 25), "Weak", "🟠"
        elif entropy <= 70:
            return int(50 + ((entropy - 50) / 20) * 25), "Good", "🟡"
        else:
            return min(100, int(75 + ((entropy - 70) / 20) * 25)), "Strong", "🟢"
    
    def analyze_weaknesses(pwd):
        """Analyze password weaknesses"""
        weaknesses = []
        
        if len(pwd) < 8:
            weaknesses.append("Too short (less than 8 characters)")
        if not re.search(r'[a-z]', pwd):
            weaknesses.append("No lowercase letters")
        if not re.search(r'[A-Z]', pwd):
            weaknesses.append("No uppercase letters")
        if not re.search(r'\d', pwd):
            weaknesses.append("No numbers")
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', pwd):
            weaknesses.append("No special characters")
        if re.search(r'(.)\1{2,}', pwd):
            weaknesses.append("Contains repeated characters")
        if re.search(r'(012|123|234|345|456|567|678|789|890)', pwd):
            weaknesses.append("Contains number sequence")
        
        return weaknesses
    
    try:
        # Analyze the password
        entropy, char_sets = calculate_entropy(password)
        scenarios = get_time_to_crack(entropy)
        score, strength, strength_icon = get_strength_info(entropy)
        weaknesses = analyze_weaknesses(password)
        
        # Create main embed
        embed = discord.Embed(
            title="🔒 Password Strength Analysis",
            description="*Comprehensive security analysis with crack-time scenarios*",
            color=0x2B2D31
        )
        
        # Strength overview
        progress_bar = create_progress_bar(score, 100, 20)
        embed.add_field(
            name="💪 **Strength Assessment**",
            value=f"**Score:** {score}/100\n**Level:** {strength_icon} **{strength}**\n**Progress:** {progress_bar}\n**Entropy:** {entropy:.1f} bits",
            inline=False
        )
        
        # Time to crack scenarios
        scenario_text = ""
        for scenario_id, info in scenarios.items():
            scenario_text += f"{info['icon']} **{info['name']}:** {info['time']}\n"
        
        embed.add_field(
            name="⏱️ **Time to Crack Scenarios**",
            value=scenario_text,
            inline=False
        )
        
        # Character analysis
        char_info = f"**Length:** {len(password)} characters\n"
        if char_sets:
            char_info += f"**Uses:** {', '.join(char_sets[:3])}"
            if len(char_sets) > 3:
                char_info += f" +{len(char_sets)-3} more"
        else:
            char_info += "**Uses:** No standard character sets"
            
        embed.add_field(
            name="📊 **Character Analysis**",
            value=char_info,
            inline=True
        )
        
        # Security issues
        if weaknesses:
            weakness_text = ""
            for weakness in weaknesses[:5]:  # Limit to 5
                weakness_text += f"⚠️ {weakness}\n"
            if len(weaknesses) > 5:
                weakness_text += f"⚠️ +{len(weaknesses)-5} more issues"
        else:
            weakness_text = "✅ No major issues detected!"
            
        embed.add_field(
            name="🔍 **Security Issues**",
            value=weakness_text,
            inline=True
        )
        
        embed.set_footer(text="🔐 Password analysis complete • Keep your passwords private")
        
        await interaction.followup.send(embed=embed)
        print(f"🔒 Password analysis completed for {interaction.user.name}")
        
    except Exception as e:
        await interaction.followup.send("❌ Password analysis failed. Please try again.", ephemeral=True)
        print(f"❌ Password analysis error: {e}")

@study_bot.tree.command(name="ping", description="Check bot response time and status")
async def ping_bot_status(interaction: discord.Interaction):
    """Check bot latency and status."""
    start_time = datetime.utcnow()
    
    # Create modern status embed
    ping_embed = discord.Embed(
        title="System Status",
        description="*Real-time health check and performance metrics*",
        color=0x2B2D31
    )
    
    # Calculate response time
    await interaction.response.send_message(embed=ping_embed)
    
    response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
    
    # Performance metrics
    ping_embed.add_field(
        name="⚡ **Performance**",
        value=f"**Response Time:** {response_time:.1f}ms\n**Gateway Latency:** {study_bot.latency * 1000:.1f}ms\n**Status:** 🟢 **Online**",
        inline=True
    )
    
    # System components
    ping_embed.add_field(
        name="🔧 **Components**",
        value=f"**Servers:** {len(study_bot.guilds)}\n**Commands:** 17 **Active**\n**Database:** ✅ **Ready**",
        inline=True
    )
    
    ping_embed.set_footer(text="🚀 All systems operational • CompTIA Study Bot ready")
    
    await interaction.edit_original_response(embed=ping_embed)
    print(f"🏓 Ping check by {interaction.user.name} - {response_time:.1f}ms")

# Export the bot instance
bot = study_bot