"""Main execution file for the RoboticHugo bot."""

import time
import logging
from datetime import datetime, timezone, timedelta

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

# --- Main Bot Logic ---


def run_bot():
    """Main function to run the bot loop."""
    log.info("--- RoboticHugo Bot Starting ---")

    # Load initial state
    access_token, refresh_token, client_id, client_secret = auth.load_tokens()
    openai_client = ai.initialize_openai_client()
    bot_user_id = None
    last_post_time = None  # Initialize in-memory timestamp

    if not openai_client:
        log.critical("Failed to initialize OpenAI client. Exiting.")
        return

    while True:
        log.debug("--- Starting Check Cycle ---")

        # 1. Check Authentication & Get User ID
        if not access_token:
            log.critical("Missing access token. Need to run authenticate.py. Exiting.")
            break

        token_valid, current_user_id = auth.test_api_call(access_token)

        if current_user_id:
            if bot_user_id != current_user_id:
                log.info(f"Bot User ID confirmed/updated: {current_user_id}")
                bot_user_id = current_user_id
        elif not bot_user_id and token_valid:
            log.warning(
                "Could not confirm Bot User ID in this cycle (needed for liking/fetching). Will retry."
            )

        # Attempt refresh if token explicitly failed validation (401)
        if not token_valid:
            log.warning("Access token test failed (401). Attempting refresh.")
            if not refresh_token:
                log.critical(
                    "Access token invalid, and no refresh token available. Please run authenticate.py manually. Exiting."
                )
                break

            new_access_token, new_refresh_token = auth.try_refresh_token(
                refresh_token, client_id, client_secret
            )

            if new_access_token:
                access_token = new_access_token  # Update token for current cycle
                refresh_token = new_refresh_token  # Update refresh token too
                log.info("Token refresh successful. Continuing cycle with new token.")
                # Re-test the new token immediately & get user ID
                token_valid, current_user_id = auth.test_api_call(access_token)
                if current_user_id:
                    bot_user_id = current_user_id
                if not token_valid:
                    log.critical("Newly refreshed token failed validation. Exiting.")
                    break
            else:
                log.error("Token refresh failed.")
                if (
                    not refresh_token
                ):  # Refresh function returns None for refresh_token if invalid grant
                    log.critical(
                        "Refresh token appears invalid. Please run authenticate.py manually. Exiting."
                    )
                    break
                log.info(
                    f"Will retry after sleep interval: {config.SLEEP_INTERVAL_SECONDS} seconds."
                )
                time.sleep(config.SLEEP_INTERVAL_SECONDS)
                continue  # Skip rest of the cycle

        # 2. Check if ready to post (Requires valid token)
        ready_to_post = False
        if token_valid:
            # Initialize last_post_time on first valid run or after restart
            if last_post_time is None and bot_user_id:
                log.info("In-memory last_post_time is None. Fetching from API...")
                last_post_time = twitter_api.get_last_tweet_time(
                    bot_user_id, access_token
                )
                if last_post_time is None:
                    log.info(
                        "No prior tweet time found via API, assuming ready to post."
                    )
                    ready_to_post = True  # Ready if no history found
            elif last_post_time is None and not bot_user_id:
                log.warning(
                    "Cannot determine last post time without Bot User ID. Assuming ready to post."
                )
                ready_to_post = True  # Allow first post if ID is unknown

            # Check the time if we have a timestamp
            if last_post_time is not None:
                now = datetime.now(timezone.utc)
                time_since_last_post = now - last_post_time
                if time_since_last_post >= timedelta(hours=config.POST_INTERVAL_HOURS):
                    log.info(
                        f"Sufficient time passed ({time_since_last_post}). Ready to post."
                    )
                    ready_to_post = True
                else:
                    log.debug(
                        f"Waiting... Time since last post: {time_since_last_post}"
                    )
            # If last_post_time is still None after check, ready_to_post might be True

        # 3. Generate, Post, and Like Tweet if ready
        if ready_to_post and token_valid:  # Ensure token is still considered valid
            log.info("Attempting to generate and post a new tweet.")
            new_tweet_text = ai.generate_smart_tweet(openai_client)

            if new_tweet_text:
                posted_ok, new_tweet_id = twitter_api.post_tweet(
                    access_token, new_tweet_text
                )

                if posted_ok:
                    now = datetime.now(timezone.utc)
                    last_post_time = now
                    log.info(f"Updated in-memory last_post_time to: {last_post_time}")

                    if new_tweet_id and bot_user_id:
                        log.info("Attempting to like the new tweet.")
                        time.sleep(2)  # Small delay before liking
                        twitter_api.like_tweet(bot_user_id, new_tweet_id, access_token)
                    elif not bot_user_id:
                        log.warning(
                            "Tweet posted, but cannot like it without Bot User ID."
                        )
                    elif not new_tweet_id:
                        log.error(
                            "Tweet posted but failed to get its ID back. Cannot like."
                        )
                else:
                    log.error("Failed to post the generated tweet.")
            else:
                log.error("Failed to generate a valid tweet this cycle.")
        elif ready_to_post and not token_valid:
            log.warning(
                "Was ready to post, but token became invalid before posting. Will retry next cycle."
            )

        # 4. Sleep
        log.info(
            f"--- Check Cycle End --- Sleeping for {config.SLEEP_INTERVAL_SECONDS} seconds ---"
        )
        time.sleep(config.SLEEP_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        run_bot()
    except KeyboardInterrupt:
        log.info("Bot stopped manually.")
    except Exception as e:
        log.critical(f"Unhandled exception in main loop: {e}", exc_info=True)
