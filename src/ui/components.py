"""Discord UI components and interactive elements"""
import discord
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.database.models import get_user_data, update_user_data  
from src.ai.openai_client import extract_topic_from_question
from src.ai.adaptive import update_topic_performance

class PracticeQuestionView(discord.ui.View):
    """
    Interactive Discord view with buttons for answering practice questions.
    
    This creates A, B, C, D buttons that users can click to submit their answers.
    Tracks scoring and provides immediate feedback, then shows next question if available.
    """
    
    def __init__(self, correct_answer: str, explanation: str, user_id: int, 
                 question_number: int, total_questions: int, remaining_questions: list, 
                 interaction_context, question_text: str = None, certification: str = None):
        super().__init__(timeout=60)
        self.correct_answer = correct_answer.upper()
        self.explanation = explanation
        self.user_id = user_id
        self.question_number = question_number
        self.total_questions = total_questions
        self.remaining_questions = remaining_questions
        self.interaction_context = interaction_context
        self.answered = False
        self.original_message = None
        self.countdown_task = None
        self.question_text = question_text
        self.certification = certification
        
    async def start_countdown(self, message):
        """Start the countdown timer for this question"""
        self.original_message = message
        self.countdown_task = asyncio.create_task(self._countdown_loop())
        
    async def _countdown_loop(self):
        """Handle the countdown timer with color changes"""
        try:
            embed = self.original_message.embeds[0] if self.original_message.embeds else None
            if not embed:
                return
                
            countdown_times = [60, 55, 50, 45, 40, 35, 30, 25, 20, 15, 10, 5]
            
            for remaining in countdown_times:
                if self.answered:
                    return
                    
                # Change color based on time remaining
                if remaining > 30:
                    embed.color = 0x7289da  # Blue - plenty of time
                elif remaining > 10: 
                    embed.color = 0xffa500  # Orange - getting urgent
                else:
                    embed.color = 0xff4444  # Red - almost out of time
                    
                embed.set_footer(text=f"⏰ Time remaining: {remaining} seconds - Click a button to answer!")
                
                try:
                    await self.original_message.edit(embed=embed, view=self)
                    await asyncio.sleep(5)  # Update every 5 seconds
                except discord.NotFound:
                    return
                except discord.HTTPException:
                    pass
                    
        except asyncio.CancelledError:
            pass
            
    async def on_timeout(self):
        """Handle timeout when user doesn't answer in time"""
        if self.answered:
            return
            
        # Disable all buttons
        for item in self.children:
            if hasattr(item, 'disabled'):
                item.disabled = True
                
        # Create timeout embed
        timeout_embed = discord.Embed(
            title="⏰ Time's Up!",
            description=f"You didn't answer in time. The correct answer was **{self.correct_answer}**.",
            color=0xff4444  # Red
        )
        
        timeout_embed.add_field(
            name="Explanation",
            value=self.explanation,
            inline=False
        )
        
        try:
            # Update the original message to show timeout
            if self.original_message:
                await self.original_message.edit(embed=timeout_embed, view=self)
                
                # Show next question if available (after timeout)
                if self.remaining_questions and self.interaction_context:
                    await asyncio.sleep(3)  # Brief pause before next question
                    await self.send_next_question_after_timeout()
                    
        except discord.NotFound:
            pass
        except discord.HTTPException:
            pass
    
    async def send_next_question_after_timeout(self):
        """Send next question after a timeout (different from normal flow)"""
        if not self.remaining_questions:
            return
            
        # Get next question data
        next_question_data = self.remaining_questions.pop(0)
        question_content = next_question_data['question']
        correct_answer = next_question_data['answer'] 
        explanation = next_question_data['explanation']
        next_question_number = self.question_number + 1
        
        # Get user data from database for cert name
        try:
            user_data = await get_user_data(self.user_id)
            cert_name = user_data.get('selected_cert', 'Unknown')
        except:
            cert_name = 'Unknown'
        
        # Create next question embed
        question_embed = discord.Embed(
            title=f"📝 Practice Question {next_question_number}/{self.total_questions} - {cert_name}",
            description=question_content,
            color=0x7289da
        )
        
        # Add the multiple choice options to the embed
        if 'options' in next_question_data:
            options_text = ""
            for letter, option in next_question_data['options'].items():
                options_text += f"**{letter.upper()})** {option}\n"
            question_embed.add_field(
                name="Answer Choices",
                value=options_text,
                inline=False
            )
        
        question_embed.set_footer(text="⏰ Time remaining: 60 seconds - Click a button to answer!")
        
        # Create new interactive view
        next_view = PracticeQuestionView(
            correct_answer=correct_answer,
            explanation=explanation,
            user_id=self.user_id,
            question_number=next_question_number,
            total_questions=self.total_questions,
            remaining_questions=self.remaining_questions,
            interaction_context=self.interaction_context,
            question_text=question_content,
            certification=cert_name
        )
        
        try:
            # Send next question
            if self.interaction_context:
                next_message = await self.interaction_context.followup.send(embed=question_embed, view=next_view)
                await next_view.start_countdown(next_message)
        except discord.HTTPException:
            pass
        except AttributeError:
            pass
        
    def check_answer(self, selected_answer: str) -> bool:
        """Check if the selected answer is correct"""
        return selected_answer.upper() == self.correct_answer
        
    async def handle_answer(self, interaction: discord.Interaction, selected_answer: str):
        """Process the user's answer and update their score"""
        if self.answered:
            await interaction.response.send_message("You already answered this question!", ephemeral=True)
            return
            
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This question isn't for you!", ephemeral=True)
            return
            
        self.answered = True
        is_correct = self.check_answer(selected_answer)
        
        # Cancel countdown timer
        if self.countdown_task:
            self.countdown_task.cancel()
        
        # Update user statistics - get from database
        user_data = await get_user_data(self.user_id, str(interaction.user.name))
        
        if is_correct:
            user_data["correct_answers"] += 1
            user_data["study_score"] += 1
            score_change = "+1"
            result_color = 0x00ff00  # Green
            result_emoji = "✅"
            feedback_title = f"Correct! Great job! 🎉"
        else:
            user_data["study_score"] -= 1
            score_change = "-1"
            result_color = 0xff4444  # Red
            result_emoji = "❌" 
            feedback_title = f"Not quite right, but keep learning! 📚"
        
        # Save updated data to database
        await update_user_data(self.user_id, user_data)
        
        # Extract topic from question for adaptive learning
        if self.question_text and self.certification:
            topic = await extract_topic_from_question(self.question_text, self.certification)
            await update_topic_performance(self.user_id, self.certification, topic, is_correct, 30)
            
        # Disable all buttons
        for item in self.children:
            if hasattr(item, 'disabled'):
                item.disabled = True
            
        # Get the original question embed to preserve it
        original_embed = self.original_message.embeds[0] if self.original_message.embeds else None
        
        # Create combined embed that shows BOTH question and result
        combined_embed = discord.Embed(
            title=f"Question {self.question_number}/{self.total_questions} • {self.certification or 'Practice'}",
            description=f"**{self.question_text}**" if self.question_text else original_embed.description if original_embed else "",
            color=result_color
        )
        
        # Add original answer choices if available
        if original_embed:
            for field in original_embed.fields:
                if "Answer Choices" in field.name or "Select your answer" in field.name:
                    combined_embed.add_field(
                        name="📝 Answer Choices",
                        value=field.value,
                        inline=False
                    )
        
        # Add modern result section with visual hierarchy
        result_header = f"{result_emoji} **{feedback_title}**"
        
        answer_comparison = f"```ansi\n"
        if is_correct:
            answer_comparison += f"\u001b[32m✅ Your Answer: {selected_answer.upper()}\u001b[0m\n"
            answer_comparison += f"\u001b[32m🎯 Correct Answer: {self.correct_answer}\u001b[0m\n"
        else:
            answer_comparison += f"\u001b[31m❌ Your Answer: {selected_answer.upper()}\u001b[0m\n"
            answer_comparison += f"\u001b[32m🎯 Correct Answer: {self.correct_answer}\u001b[0m\n"
        answer_comparison += f"\u001b[36m📊 Score: {score_change} (Total: {user_data['study_score']})\u001b[0m\n```"
        
        combined_embed.add_field(
            name=result_header,
            value=answer_comparison,
            inline=False
        )
        
        # Add explanation with better formatting
        explanation_text = f"💡 **Explanation:**\n{self.explanation}"
        combined_embed.add_field(
            name="\u200b",  # Invisible character for spacing
            value=explanation_text,
            inline=False
        )
        
        # Add completion status
        combined_embed.set_footer(
            text=f"Question {self.question_number}/{self.total_questions} completed • {len(self.remaining_questions)} remaining"
        )
        
        # Update message with combined question + result
        await interaction.response.edit_message(embed=combined_embed, view=self)
        print(f"📝 {interaction.user.name} answered {selected_answer} - {'✅ Correct' if is_correct else '❌ Wrong'} (Score: {user_data['study_score']})")
        
        # Brief pause before showing next question
        await asyncio.sleep(2)
        await self.send_next_question(interaction)

    async def send_next_question(self, interaction: discord.Interaction):
        """Send the next question in the sequence"""
        if not self.remaining_questions:
            # No more questions - show completion message
            completion_embed = discord.Embed(
                title="🎉 Practice Session Complete!",
                description=f"Great job! You completed all {self.total_questions} questions.",
                color=0x00ff00
            )
            
            try:
                user_data = await get_user_data(self.user_id)
                if user_data['total_questions'] > 0:
                    accuracy = (user_data['correct_answers']/user_data['total_questions']*100)
                else:
                    accuracy = 0
                completion_embed.add_field(
                    name="📊 Session Summary",
                    value=f"Score: {user_data['study_score']} | Total Questions: {user_data['total_questions']} | Accuracy: {accuracy:.1f}%",
                    inline=False
                )
            except:
                completion_embed.add_field(
                    name="📊 Session Summary",
                    value="Great work completing the questions!",
                    inline=False
                )
            completion_embed.add_field(
                name="🚀 Keep Learning",
                value="Use `/practice` again for more questions or try `/pomodoro study` for focused sessions!",
                inline=False
            )
            
            await interaction.followup.send(embed=completion_embed)
            return
        
        # Get next question data
        next_question_data = self.remaining_questions.pop(0)
        question_content = next_question_data['question']
        correct_answer = next_question_data['answer'] 
        explanation = next_question_data['explanation']
        next_question_number = self.question_number + 1
        
        # Get user data from database for cert name
        try:
            user_data = await get_user_data(self.user_id)
            cert_name = user_data.get('selected_cert', 'Unknown')
        except:
            cert_name = 'Unknown'
            
        # Create modern, professional question embed
        question_embed = discord.Embed(
            title=f"Practice Question {next_question_number}/{self.total_questions}",
            description=f"**{question_content}**",
            color=0x2B2D31  # Professional dark theme
        )
        
        # Add certification badge
        question_embed.set_author(
            name=f"📚 {cert_name} Certification Practice"
        )
        
        # Add the multiple choice options with modern styling
        if 'options' in next_question_data:
            options_text = "```\n"
            for letter, option in next_question_data['options'].items():
                options_text += f"{letter.upper()})  {option}\n"
            options_text += "```"
            question_embed.add_field(
                name="📝 Select your answer:",
                value=options_text,
                inline=False
            )
        
        # Add progress bar visual
        progress_filled = "█" * next_question_number
        progress_empty = "░" * (self.total_questions - next_question_number)
        progress_bar = f"```[{progress_filled}{progress_empty}] {next_question_number}/{self.total_questions}```"
        
        question_embed.add_field(
            name="📊 Progress",
            value=progress_bar,
            inline=False
        )
        
        question_embed.set_footer(
            text="⏰ 60 seconds to answer • Choose A, B, C, or D below"
        )
        
        # Create new interactive view
        next_view = PracticeQuestionView(
            correct_answer=correct_answer,
            explanation=explanation,
            user_id=self.user_id,
            question_number=next_question_number,
            total_questions=self.total_questions,
            remaining_questions=self.remaining_questions,
            interaction_context=self.interaction_context,
            question_text=question_content,
            certification=cert_name
        )
        
        # Send next question
        next_message = await interaction.followup.send(embed=question_embed, view=next_view)
        await next_view.start_countdown(next_message)

    @discord.ui.button(label='A', style=discord.ButtonStyle.primary, emoji='🅰️')
    async def answer_a(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_answer(interaction, 'A')
        
    @discord.ui.button(label='B', style=discord.ButtonStyle.primary, emoji='🅱️') 
    async def answer_b(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_answer(interaction, 'B')
        
    @discord.ui.button(label='C', style=discord.ButtonStyle.primary, emoji='🔴')
    async def answer_c(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_answer(interaction, 'C')
        
    @discord.ui.button(label='D', style=discord.ButtonStyle.primary, emoji='🔵')
    async def answer_d(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_answer(interaction, 'D')