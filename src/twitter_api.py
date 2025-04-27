"""Functions for interacting with specific X API v2 endpoints."""

import logging
import requests
from datetime import datetime

# Assuming config.py is in the same directory or PYTHONPATH
import config

log = logging.getLogger(__name__)


def get_last_tweet_time(user_id, access_token):
    """Gets the timestamp of the user's single last original tweet (optimized)."""
    if not user_id:
        log.error("Cannot get last tweet time without user ID.")
        return None

    log.info(
        f"Fetching last tweet for user ID: {user_id} to initialize last post time..."
    )
    api_url = f"{config.X_API_BASE_URL}/users/{user_id}/tweets"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "exclude": "replies,retweets",
        "max_results": 5,
        "tweet.fields": "created_at",
    }
    try:
        # response = requests.get(
        #     api_url,
        #     headers=headers,
        #     params=params,
        #     timeout=config.TIMEOUT_GET_TWEETS
        # )
        # response.raise_for_status()
        # tweets_data = response.json()
        tweets_data = {}

        if tweets_data.get("meta", {}).get("result_count", 0) > 0:
            last_tweet = tweets_data.get("data", [])[0]
            last_tweet_time_str = last_tweet.get("created_at")
            # Ensure the string is not None before parsing
            if last_tweet_time_str:
                last_tweet_time = datetime.fromisoformat(last_tweet_time_str)
                log.info(f"Last original tweet time found via API: {last_tweet_time}")
                return last_tweet_time
            else:
                log.error("Found last tweet but 'created_at' field was missing.")
                return None
        else:
            log.info("No original tweets found for this user via API.")
            return None

    except requests.exceptions.RequestException as e:
        log.error(f"Failed to fetch user tweets: {e}")
        if e.response is not None:
            log.error(f"Fetch tweets response status: {e.response.status_code}")
            log.error(f"Fetch tweets response body: {e.response.text}")
        return None
    except Exception as e:
        log.error(f"Unexpected error fetching last tweet time: {e}", exc_info=True)
        return None


def post_tweet(access_token, tweet_text):
    """Posts a tweet using the provided access token via direct requests."""
    if not access_token or not tweet_text:
        log.error("Missing access token or tweet text for posting.")
        return False, None

    tweet_payload = {"text": tweet_text}
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    api_url = f"{config.X_API_BASE_URL}/tweets"
    tweet_id = None
    try:
        log.info(
            f"Attempting to post tweet directly to {api_url}: '{tweet_text[:50]}...'"
        )
        response = requests.post(
            api_url,
            headers=headers,
            json=tweet_payload,
            timeout=config.TIMEOUT_POST_TWEET,
        )
        response.raise_for_status()
        response_data = response.json()
        tweet_id = response_data.get("data", {}).get("id")
        log.info(
            f"Successfully posted tweet via direct request! Response: {response_data}"
        )
        if tweet_id:
            print(f"Success! Tweet posted: https://x.com/roboticHugo/status/{tweet_id}")
            return True, tweet_id
        else:
            log.error(
                f"Tweet possibly posted, but could not find ID in response: {response_data}"
            )
            return False, None
    except requests.exceptions.RequestException as e:
        log.error(f"Failed to post tweet via direct request: {e}")
        if e.response is not None:
            log.error(f"Post tweet response status: {e.response.status_code}")
            log.error(f"Post tweet response body: {e.response.text}")
        return False, None
    except Exception as e:
        log.error(
            f"An unexpected error occurred during direct tweet posting: {e}",
            exc_info=True,
        )
        return False, None


def like_tweet(user_id, tweet_id, access_token):
    """Likes a specific tweet for the authenticated user."""
    if not user_id or not tweet_id or not access_token:
        log.error("Cannot like tweet without user_id, tweet_id, and access_token.")
        return False

    api_url = f"{config.X_API_BASE_URL}/users/{user_id}/likes"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {"tweet_id": tweet_id}
    log.info(f"Attempting to like tweet ID: {tweet_id} for user ID: {user_id}")
    try:
        response = requests.post(
            api_url, headers=headers, json=payload, timeout=config.TIMEOUT_LIKE_TWEET
        )
        response.raise_for_status()
        response_data = response.json()
        if response_data.get("data", {}).get("liked") is True:
            log.info(f"Successfully liked tweet {tweet_id}.")
            return True
        else:
            # This case might indicate an issue or change in API response
            log.warning(
                f"Like request succeeded (status {response.status_code}) but response indicates not liked? {response_data}"
            )
            return False

    except requests.exceptions.RequestException as e:
        log.error(f"Failed to like tweet {tweet_id}: {e}")
        if e.response is not None:
            log.error(f"Like tweet response status: {e.response.status_code}")
            try:
                response_text = e.response.text
                log.error(f"Like tweet response body: {response_text}")
                # Handle potential 403 if already liked
                if e.response.status_code == 403 and (
                    "already liked" in response_text.lower()
                    or "You have already liked this Tweet" in response_text
                ):
                    log.warning(f"Tweet {tweet_id} was already liked.")
                    return True  # Treat as success if already liked
            except Exception:
                log.error("Could not read like tweet error response body.")
        return False

    except Exception as e:
        log.error(
            f"An unexpected error occurred during liking tweet: {e}", exc_info=True
        )
        return False
