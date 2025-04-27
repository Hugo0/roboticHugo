"""Helper functions for interacting with OpenAI API."""

import logging
import os
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# Assuming config.py is in the same directory or PYTHONPATH
import config

log = logging.getLogger(__name__)


def initialize_openai_client():
    """Initializes and returns the OpenAI client."""
    load_dotenv(dotenv_path=config.ENV_FILE)  # Ensure API key is loaded
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        log.error("OPENAI_API_KEY not found in environment variables.")
        return None
    try:
        client = OpenAI(api_key=openai_api_key)
        log.info("OpenAI client initialized.")
        return client
    except Exception as e:
        log.error(f"Failed to initialize OpenAI client: {e}")
        return None


def sanitize_ai_response(text):
    """Basic sanitization for AI response"""
    if not isinstance(text, str):
        log.warning(f"Attempted to sanitize non-string input: {type(text)}")
        return ""
    # split on <final_tweet> and take the last part
    text = text.split("<final_tweet>")[1].split("</final_tweet>")[0]
    log.info(f"text after splitting on <final_tweet>: \n{text}")

    # Remove leading/trailing whitespace and common quote characters
    text = text.strip().strip('"').strip("'").strip("`").strip()

    # Prevent empty tweets
    if not text:
        log.warning("AI response was empty after sanitization.")
        return None  # Signal failure to generate valid text

    # replace em dashes with -
    text = text.replace("—", "-")

    # Simple length check (Twitter limit is 280)
    # Use character count directly
    if len(text) > 280:
        log.warning(f"AI response exceeds 280 chars ({len(text)}), truncating.")
        # Truncate carefully to avoid cutting mid-word if possible, though simple slice is easier
        text = text[:277] + "..."

    return text


def generate_smart_tweet(openai_client, prompt_override=None):
    """Generates a tweet using OpenAI API. Allows overriding the default prompt."""
    if not openai_client:
        log.error("OpenAI client not provided for generation.")
        return None

    # Use override if provided, otherwise use the default
    if prompt_override:
        prompt = prompt_override
        log.info("Using provided prompt override.")
    else:
        # Default prompt
        prompt = f"""
Think about a few tweets or shitposts that you would like to write. Then find the one that would perform best on twitter. Your response should include the tokens <final_tweet> before the final tweet text.
"""
        log.info("Using default prompt.")

    log.info(
        f"Generating tweet with prompt: '{prompt[:100]}...' using {config.OPENAI_MODEL}"
    )

    try:
        response = openai_client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a twitter persona that write actually useful, insightful, and slightly provocative tweets. Role Models are Paul Graham, Naval Ravikant.",
                },
                {"role": "user", "content": prompt},
            ],
            max_completion_tokens=5000,
            n=3,
            stop=None,
        )

        ai_text = response.choices[0].message.content
        log.info(f"Raw AI response: {ai_text}")

        sanitized_tweet = sanitize_ai_response(ai_text)
        if sanitized_tweet:
            log.info(f"Sanitized tweet: {sanitized_tweet}")
            return sanitized_tweet
        else:
            log.error("AI response was empty or invalid after sanitization.")
            return None

    except Exception as e:
        log.error(f"Failed to generate tweet using OpenAI: {e}", exc_info=True)
        return None
