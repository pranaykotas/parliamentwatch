"""Committee configuration and API mappings for sansad.in."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base paths — relative to this file's location, not cwd
_SCRIPT_DIR = Path(__file__).resolve().parent

BASE_URL = "https://sansad.in"

# API endpoint for committee reports
REPORTS_API = f"{BASE_URL}/api_ls/committee/lsRSAllReports"

# Lok Sabha number (configurable via env or CLI)
CURRENT_LOK_SABHA = int(os.getenv("LOK_SABHA_NUMBER", "18"))

# All 16 Departmentally Related Standing Committees (DRSCs)
# The 'api_code' is the committeeCode used in the sansad.in API
DRSC_COMMITTEES = {
    "agriculture": {
        "name": "Agriculture, Animal Husbandry and Food Processing",
        "api_code": 5,
    },
    "chemicals": {
        "name": "Chemicals & Fertilizers",
        "api_code": 45,
    },
    "coal": {
        "name": "Coal, Mines and Steel",
        "api_code": 46,
    },
    "defence": {
        "name": "Defence",
        "api_code": 7,
    },
    "energy": {
        "name": "Energy",
        "api_code": 9,
    },
    "external_affairs": {
        "name": "External Affairs",
        "api_code": 11,
    },
    "finance": {
        "name": "Finance",
        "api_code": 12,
    },
    "consumer_affairs": {
        "name": "Consumer Affairs, Food and Public Distribution",
        "api_code": 13,
    },
    "communications": {
        "name": "Communications and Information Technology",
        "api_code": 18,
    },
    "labour": {
        "name": "Labour, Textiles and Skill Development",
        "api_code": 19,
    },
    "petroleum": {
        "name": "Petroleum & Natural Gas",
        "api_code": 23,
    },
    "railways": {
        "name": "Railways",
        "api_code": 28,
    },
    "rural_development": {
        "name": "Rural Development and Panchayati Raj",
        "api_code": 32,
    },
    "social_justice": {
        "name": "Social Justice & Empowerment",
        "api_code": 47,
    },
    "housing": {
        "name": "Housing and Urban Affairs",
        "api_code": 41,
    },
    "water_resources": {
        "name": "Water Resources",
        "api_code": 44,
    },
}

# LLM settings — defaults to Anthropic for backward compatibility
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")  # "anthropic" or "openai"
LLM_MODEL = os.getenv("LLM_MODEL", "")  # defaults per provider if empty
LLM_API_KEY = os.getenv("LLM_API_KEY", os.getenv("ANTHROPIC_API_KEY", ""))
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")  # for OpenAI-compatible endpoints

# Email settings (configurable via .env)
NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")

# Data paths — default to {script_dir}/data, overridable via env
DATA_DIR = os.getenv("DATA_DIR", str(_SCRIPT_DIR / "data"))
REPORTS_JSON = os.path.join(DATA_DIR, "reports.json")
PDFS_DIR = os.path.join(DATA_DIR, "pdfs")
TEXT_DIR = os.path.join(DATA_DIR, "text")
SUMMARIES_DIR = os.path.join(DATA_DIR, "summaries")
COMMITTEE_MEMBERS_JSON = os.path.join(DATA_DIR, "committee_members.json")
