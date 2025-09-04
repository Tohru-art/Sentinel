"""Bot Configuration"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot Configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Active Developer Badge Configuration
CHANNEL_ID = 1410176690663067730  # Replace with your Discord channel ID

# CompTIA Certification Data
COMPTIA_CERTS = {
    "A+": {
        "name": "CompTIA A+ (Core 1 & Core 2)",
        "description": "Entry-level IT certification covering hardware, networking, mobile devices, and troubleshooting",
        "domains": [
            "Mobile Devices", "Networking", "Hardware", "Virtualization and Cloud Computing",
            "Hardware and Network Troubleshooting", "Operating Systems", "Security",
            "Software Troubleshooting", "Operational Procedures"
        ]
    },
    "Security+": {
        "name": "CompTIA Security+",
        "description": "Foundation-level cybersecurity certification",
        "domains": [
            "Attacks, Threats, and Vulnerabilities", "Architecture and Design",
            "Implementation", "Operations and Incident Response",
            "Governance, Risk, and Compliance"
        ]
    },
    "Network+": {
        "name": "CompTIA Network+",
        "description": "Networking fundamentals certification",
        "domains": [
            "Networking Fundamentals", "Network Implementations",
            "Network Operations", "Network Security", "Network Troubleshooting"
        ]
    },
    "CySA+": {
        "name": "CompTIA Cybersecurity Analyst (CySA+)",
        "description": "Intermediate cybersecurity analyst certification",
        "domains": [
            "Threat and Vulnerability Management", "Software and Systems Security",
            "Security Operations and Monitoring", "Incident Response",
            "Compliance and Assessment"
        ]
    }
}

# Cybersecurity Quotes
CYBER_QUOTES = [
    "Cybersecurity is not a product, but a process. – Bruce Schneier",
    "There are only two types of companies in the world: those that have been breached and know it, and those that have been breached and don't know it yet",
    "It takes 20 years to build a reputation and a few minutes of a cyber-incident to ruin it",
    "Total security would mean no connectivity—cybersecurity is about balance",
    "Security is always excessive until it's not enough. – Robbie Sinclair",
    "Only amateurs attack machines. Professionals target people. – Bruce Schneier",
]

# Utility functions
def validate_question_count(count, max_allowed=5):
    """Validate and clamp question count to allowed range"""
    if count < 1:
        return 1
    elif count > max_allowed:
        return max_allowed
    return count

def format_study_domains_list(domains):
    """Format domains list for display"""
    return '\n'.join([f"• {domain}" for domain in domains])