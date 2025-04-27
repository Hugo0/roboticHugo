"""Configuration settings for the RoboticHugo bot."""

import logging

# --- File Paths ---
ENV_FILE = ".env"

# --- Logging ---
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# --- Timing ---
# Time between checks in the main loop (seconds)
SLEEP_INTERVAL_SECONDS = 60 * 60  # 1 hour
# Minimum time before posting a new tweet (hours)
POST_INTERVAL_HOURS = 24

# --- APIs ---
OPENAI_MODEL = "o3-mini"
X_API_BASE_URL = "https://api.twitter.com/2"

# --- Timeouts (seconds) ---
TIMEOUT_API_TEST = 10
TIMEOUT_GET_TWEETS = 15
TIMEOUT_POST_TWEET = 30
TIMEOUT_LIKE_TWEET = 15
TIMEOUT_REFRESH_TOKEN = 20
