"""Utility functions and helpers"""

def create_progress_bar(value, max_value, length=16):
    """Create a modern progress bar visualization"""
    if max_value == 0:
        percentage = 0
    else:
        percentage = min(value / max_value, 1.0)  # Cap at 100%
    
    filled = int(length * percentage)
    empty = length - filled
    
    # Use different colors based on percentage
    if percentage >= 0.8:
        bar_char = "🟩"  # Green for excellent
    elif percentage >= 0.6:
        bar_char = "🟨"  # Yellow for good
    else:
        bar_char = "🟥"  # Red for needs improvement
    
    bar = bar_char * filled + "⬜" * empty
    return f"{bar} **{percentage*100:.1f}%**"

def create_clean_stats_table(data_rows):
    """Create a clean, aligned stats table"""
    if not data_rows:
        return "```\nNo data available\n```"
    
    # Find max widths for alignment
    max_name_width = max(len(row[0]) for row in data_rows)
    max_acc_width = max(len(f"{row[1]:.1f}%") for row in data_rows)
    
    table = "```\n"
    for name, accuracy, questions in data_rows:
        name_padded = name[:24].ljust(min(24, max_name_width))
        acc_padded = f"{accuracy:.1f}%".rjust(max_acc_width)
        table += f"{name_padded}  {acc_padded}  {questions:>3} questions\n"
    table += "```"
    return table

def get_rank_display(position):
    """Get clean rank display for leaderboard position"""
    return f"#{position}"

def get_skill_tier(score, questions):
    """Get skill tier based on performance"""
    if score >= 100:
        return "LEGEND"
    elif score >= 50:
        return "EXPERT" 
    elif score >= 25:
        return "ADVANCED"
    elif questions >= 20:
        return "INTERMEDIATE"
    else:
        return "BEGINNER"