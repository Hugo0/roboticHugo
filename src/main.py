"""Main execution file for the RoboticHugo bot with Flask health check."""

import time
import logging
import threading
import psutil  # For memory usage
import os
from datetime import datetime, timezone, timedelta
from flask import Flask, jsonify, render_template

# Import local modules
import config
import auth
import twitter_api
import ai

# --- Logging Setup ---
# Configure root logger
logging.basicConfig(level=config.LOG_LEVEL, format=config.LOG_FORMAT)
# Get logger for this module
log = logging.getLogger(__name__)


# --- Bot State Class ---
class BotState:
    def __init__(self):
        log.info("Initializing Bot State...")
        self.access_token, self.refresh_token, self.client_id, self.client_secret = (
            auth.load_tokens()
        )
        self.openai_client = ai.initialize_openai_client()
        self.bot_user_id = None
        self.last_post_time = None  # Initialize in-memory timestamp
        self.last_check_start_time = None
        self.last_refresh_time = (
            None  # Time the access token was last obtained/refreshed
        )
        self.last_error = None  # Store last major error
        self.status = "Initializing"

        if not self.openai_client:
            log.critical("Failed to initialize OpenAI client.")
            self.status = "Error: OpenAI Init Failed"
        elif not self.access_token:
            log.critical("Missing initial access token.")
            self.status = "Error: Missing Access Token"
        else:
            # Set initial refresh time if token loaded successfully
            self.last_refresh_time = datetime.now(timezone.utc)
            self.status = "Initialized"
            log.info("Bot State Initialized.")

    def run_cycle(self):
        """Performs one check cycle of the bot."""
        if self.status.startswith("Error"):
            log.warning(f"Bot is in error state ({self.status}), skipping cycle.")
            return  # Don't run cycle if in error state

        self.last_check_start_time = datetime.now(timezone.utc)
        self.last_error = None  # Clear last error at start of cycle
        log.debug("--- Starting Check Cycle ---")
        self.status = "Running Check Cycle"

        try:
            # 1. Check Authentication & Get User ID
            if not self.access_token:
                log.critical(
                    "Missing access token. Need to run authenticate.py. Halting bot loop."
                )
                self.status = "Error: Missing Access Token (Runtime)"
                self.last_error = self.status
                return  # Stop this cycle, will halt loop in main thread

            token_valid, current_user_id = auth.test_api_call(self.access_token)

            if current_user_id:
                if self.bot_user_id != current_user_id:
                    log.info(f"Bot User ID confirmed/updated: {current_user_id}")
                    self.bot_user_id = current_user_id
            elif not self.bot_user_id and token_valid:
                log.warning(
                    "Could not confirm Bot User ID in this cycle. Like/fetch may fail."
                )

            if not token_valid:
                log.warning("Access token test failed (401). Attempting refresh.")
                if not self.refresh_token:
                    log.critical(
                        "Access token invalid, and no refresh token available. Halting bot loop."
                    )
                    print("Please run authenticate.py manually to re-authorize.")
                    self.status = "Error: Invalid Access & Refresh Token"
                    self.last_error = self.status
                    return  # Stop cycle

                new_access_token, new_refresh_token = auth.try_refresh_token(
                    self.refresh_token, self.client_id, self.client_secret
                )

                if new_access_token:
                    self.access_token = new_access_token
                    self.refresh_token = new_refresh_token
                    self.last_refresh_time = datetime.now(timezone.utc)
                    log.info("Token refresh successful.")
                    # Re-test the new token immediately & get user ID
                    token_valid, current_user_id = auth.test_api_call(self.access_token)
                    if current_user_id:
                        self.bot_user_id = current_user_id
                    if not token_valid:
                        log.critical(
                            "Newly refreshed token failed validation! Halting bot loop."
                        )
                        self.status = "Error: Refreshed Token Invalid"
                        self.last_error = self.status
                        return  # Stop cycle
                else:
                    log.error("Token refresh failed.")
                    self.status = "Error: Token Refresh Failed"
                    if not self.refresh_token:
                        log.critical(
                            "Refresh token became invalid during failed refresh. Halting bot loop."
                        )
                        self.last_error = self.status + " (Invalid Refresh Token)"
                        return  # Stop cycle
                    else:  # Network or other error, will retry next cycle
                        self.last_error = self.status + " (Will Retry)"
                        # Allow loop to continue to sleep and retry
                        pass

            # Only proceed if token is considered valid after potential refresh
            if not token_valid:
                log.warning(
                    "Token still invalid after check/refresh attempt. Skipping rest of cycle."
                )
                return

            # 2. Check if ready to post
            ready_to_post = self._check_if_ready_to_post()

            # 3. Generate, Post, and Like Tweet if ready
            if ready_to_post:
                self._generate_post_and_like()

            self.status = "Idle"

        except Exception as e:
            log.critical(f"Unhandled exception in check cycle: {e}", exc_info=True)
            self.status = f"Error: Unhandled Exception in Cycle"
            self.last_error = str(e)
            # Allow loop to continue to sleep and retry? Or halt?
            # Let's allow it to continue for now, but log critically.

        log.debug("--- Check Cycle End --- ")

    def _check_if_ready_to_post(self):
        """Internal helper to check posting time."""
        now = datetime.now(timezone.utc)
        # Initialize last_post_time on first valid run or after restart
        if self.last_post_time is None and self.bot_user_id:
            log.info("In-memory last_post_time is None. Fetching from API...")
            api_last_post_time = twitter_api.get_last_tweet_time(
                self.bot_user_id, self.access_token
            )

            if api_last_post_time is not None:
                self.last_post_time = api_last_post_time
                log.info(f"Initialized last_post_time from API: {self.last_post_time}")
            else:
                log.warning(
                    "Failed to get last tweet time from API. Setting 12-hour fallback."
                )
                fallback_time = now - timedelta(hours=(config.POST_INTERVAL_HOURS - 12))
                self.last_post_time = fallback_time
                log.info(f"Set fallback last_post_time to: {self.last_post_time}")

        if self.last_post_time is None:
            log.warning(
                "Cannot determine last post time yet (might need Bot User ID). Assuming not ready."
            )
            return False
        else:
            time_since_last_post = now - self.last_post_time
            if time_since_last_post >= timedelta(hours=config.POST_INTERVAL_HOURS):
                log.info(
                    f"Sufficient time passed ({time_since_last_post}). Ready to post."
                )
                return True
            else:
                log.debug(f"Waiting... Time since last post: {time_since_last_post}")
                return False

    def _generate_post_and_like(self):
        """Internal helper to generate, post, and like a tweet."""
        log.info("Attempting to generate and post a new tweet.")
        self.status = "Generating Tweet"
        new_tweet_text = ai.generate_smart_tweet(self.openai_client)

        if new_tweet_text:
            self.status = "Posting Tweet"
            posted_ok, new_tweet_id = twitter_api.post_tweet(
                self.access_token, new_tweet_text
            )

            if posted_ok:
                now = datetime.now(timezone.utc)
                self.last_post_time = now
                log.info(f"Updated in-memory last_post_time to: {self.last_post_time}")

                if new_tweet_id and self.bot_user_id:
                    log.info("Attempting to like the new tweet.")
                    self.status = "Liking Tweet"
                    time.sleep(2)  # Small delay before liking
                    twitter_api.like_tweet(
                        self.bot_user_id, new_tweet_id, self.access_token
                    )
                elif not self.bot_user_id:
                    log.warning("Tweet posted, but cannot like it without Bot User ID.")
                elif not new_tweet_id:
                    log.error(
                        "Tweet posted but failed to get its ID back. Cannot like."
                    )
            else:
                log.error("Failed to post the generated tweet.")
                self.last_error = "Failed to post tweet"
                # Do not update last_post_time if post failed
        else:
            log.error("Failed to generate a valid tweet this cycle.")
            self.last_error = "Failed to generate tweet"


# --- Flask App ---
app = Flask(__name__)
# Create a single instance of the bot state, accessible by Flask routes and the bot loop
bot_state = BotState()


@app.route("/healthz")
def health_check():
    """Health check endpoint."""
    now = datetime.now(timezone.utc)
    health_status = "OK"

    # Check token status
    token_age = None
    estimated_time_left = None
    token_status = "Unknown"
    if bot_state.last_refresh_time:
        token_age_delta = now - bot_state.last_refresh_time
        token_age = str(token_age_delta)
        # Assume 2 hour validity (7200s)
        time_left_seconds = 7200 - token_age_delta.total_seconds()
        if time_left_seconds > 0:
            estimated_time_left = str(timedelta(seconds=int(time_left_seconds)))
            token_status = "Likely Valid"
        else:
            estimated_time_left = "Expired"
            token_status = "Likely Expired"

    # Check overall bot status
    if bot_state.status.startswith("Error"):
        health_status = "Error"

    # Get memory usage
    process = psutil.Process(os.getpid())
    memory_mb = process.memory_info().rss / (1024 * 1024)  # Resident Set Size in MB

    response_data = {
        "status": health_status,
        "bot_status": bot_state.status,
        "bot_user_id": bot_state.bot_user_id,
        "timestamp_utc": now.isoformat(),
        "last_check_start_time_utc": (
            bot_state.last_check_start_time.isoformat()
            if bot_state.last_check_start_time
            else None
        ),
        "last_post_time_utc": (
            bot_state.last_post_time.isoformat() if bot_state.last_post_time else None
        ),
        "last_refresh_time_utc": (
            bot_state.last_refresh_time.isoformat()
            if bot_state.last_refresh_time
            else None
        ),
        "access_token_status": token_status,
        "access_token_age": token_age,
        "access_token_estimated_time_left": estimated_time_left,
        "memory_usage_mb": round(memory_mb, 2),
        "last_error": bot_state.last_error,
    }
    return jsonify(response_data)


@app.route("/")
def index():
    """Main page of the Flask app - renders index.html."""
    # Render the template located in the 'templates' folder
    return render_template("index.html")


# --- Background Bot Loop ---
def run_bot_loop():
    """Function to run the bot's check cycle repeatedly in a thread."""
    # Small delay at start to allow Flask server to initialize?
    time.sleep(5)

    while True:
        # Check if the bot state indicates a fatal error requiring manual intervention
        if (
            bot_state.status == "Error: Missing Access Token (Runtime)"
            or bot_state.status == "Error: Invalid Access & Refresh Token"
            or (
                bot_state.last_error and "Invalid Refresh Token" in bot_state.last_error
            )
        ):
            log.critical(
                f"Halting bot loop due to critical error state: {bot_state.status} / {bot_state.last_error}"
            )
            break  # Exit the loop

        bot_state.run_cycle()
        log.info(
            f"--- Sleeping for {config.SLEEP_INTERVAL_SECONDS} seconds --- (Current Status: {bot_state.status})"
        )
        time.sleep(config.SLEEP_INTERVAL_SECONDS)


# --- Main Execution ---
if __name__ == "__main__":
    log.info("Starting background bot loop thread...")
    bot_thread = threading.Thread(target=run_bot_loop, daemon=True)
    bot_thread.start()

    log.info("Starting Flask server...")
    # Use host='0.0.0.0' to be accessible externally (e.g., within Render network)
    # Use debug=False for production
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=False)
