"""Handles X API v2 Authentication (OAuth 2.0 PKCE) including token refresh."""

import os
import logging
import requests
from dotenv import load_dotenv, set_key

# Assuming config.py is in the same directory or PYTHONPATH
import config

log = logging.getLogger(__name__)  # Use module-specific logger


def load_tokens():
    """Loads access, refresh tokens, client ID/secret from the .env file."""
    load_dotenv(dotenv_path=config.ENV_FILE)
    access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
    refresh_token = os.environ.get("TWITTER_REFRESH_TOKEN")
    client_id = os.environ.get("TWITTER_CLIENT_ID")
    client_secret = os.environ.get("TWITTER_CLIENT_SECRET")
    log.info(
        f"Loaded tokens from {config.ENV_FILE}. AccessToken: {'Yes' if access_token else 'No'}, RefreshToken: {'Yes' if refresh_token else 'No'}"
    )
    if not client_id:
        log.error(
            "TWITTER_CLIENT_ID not found in environment variables (needed for refresh)."
        )
    # Note: OpenAI key is loaded separately in main/ai
    return access_token, refresh_token, client_id, client_secret


def save_tokens(access_token, refresh_token):
    """Saves the access and refresh tokens to the .env file."""
    # Ensure ENV_FILE path is correct if called from different contexts
    # (though config should handle this)
    env_path = os.path.abspath(config.ENV_FILE)
    try:
        log.info(f"Attempting to save tokens to {env_path}")

        # Handle Access Token
        if isinstance(access_token, str) and access_token:
            set_key(env_path, "TWITTER_ACCESS_TOKEN", access_token)
            log.info("Saved TWITTER_ACCESS_TOKEN.")
        elif access_token is None:
            # If explicitly passed None, maybe clear it? Or just skip.
            # Let's skip saving if None.
            log.warning("Skipping save for TWITTER_ACCESS_TOKEN (value was None).")
        else:  # Includes empty string
            set_key(
                env_path, "TWITTER_ACCESS_TOKEN", ""
            )  # Save empty string if provided
            log.warning("Saved empty value for TWITTER_ACCESS_TOKEN.")

        # Handle Refresh Token
        if isinstance(refresh_token, str) and refresh_token:
            set_key(env_path, "TWITTER_REFRESH_TOKEN", refresh_token)
            log.info("Saved TWITTER_REFRESH_TOKEN.")
        elif refresh_token == "":  # Explicitly clearing the refresh token
            set_key(env_path, "TWITTER_REFRESH_TOKEN", "")
            log.warning("Cleared TWITTER_REFRESH_TOKEN in env file.")
        else:  # Includes None
            log.warning("Skipping save for TWITTER_REFRESH_TOKEN (value was None).")

        return True
    except Exception as e:
        log.error(f"Failed to save tokens to {env_path}: {e}", exc_info=True)
        print(
            f"Error: Could not automatically save tokens to {env_path}. Bot may fail on next run."
        )
        return False


def try_refresh_token(refresh_token, client_id, client_secret):
    """Attempts to refresh the access token using the refresh token via direct request."""
    log.warning("Attempting to refresh access token...")
    if not refresh_token:
        log.error("Cannot refresh: No refresh token provided.")
        return None, None
    if not client_id:
        log.error("Cannot refresh: TWITTER_CLIENT_ID not found.")
        return None, None

    token_url = f"{config.X_API_BASE_URL}/oauth2/token"
    payload = {
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
        "client_id": client_id,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    auth = (client_id, client_secret) if client_secret else None

    try:
        response = requests.post(
            token_url,
            headers=headers,
            data=payload,
            auth=auth,
            timeout=config.TIMEOUT_REFRESH_TOKEN,
        )
        response.raise_for_status()

        new_token_data = response.json()
        new_access_token = new_token_data.get("access_token")
        # Keep old refresh token if a new one isn't explicitly provided
        new_refresh_token = new_token_data.get("refresh_token", refresh_token)
        expires_in = new_token_data.get("expires_in")

        if not new_access_token:
            log.error("Refresh response successful but no access_token found.")
            return None, refresh_token  # Return old refresh token, signal failure

        log.info(
            f"Successfully refreshed access token (new one expires in {expires_in}s)."
        )

        # Save the new tokens immediately
        if save_tokens(new_access_token, new_refresh_token):
            return new_access_token, new_refresh_token
        else:
            log.error(
                "Save tokens after refresh failed. Returning new tokens but they aren't persisted."
            )
            return new_access_token, new_refresh_token

    except requests.exceptions.RequestException as e:
        log.error(f"Token refresh HTTP request failed: {e}")
        if e.response is not None:
            log.error(f"Refresh Response status: {e.response.status_code}")
            try:
                response_text = e.response.text
                log.error(f"Refresh Response body: {response_text}")
                # Check for specific error indicating invalid refresh token
                if e.response.status_code in [400, 401] and (
                    "invalid_request" in response_text
                    or "invalid_grant" in response_text
                ):
                    print("Error: Refresh token is invalid or revoked.")
                    print("Please run authenticate.py manually to re-authorize.")
                    # Clear the invalid refresh token, don't try saving access token here
                    save_tokens(access_token=None, refresh_token="")
                    return None, None  # Signal hard failure
                else:
                    print(f"Error refreshing token: {e.response.status_code}")
            except Exception:
                print(
                    f"Error refreshing token: {e.response.status_code} (Could not parse body)"
                )
        else:
            print(f"Error refreshing token (network issue?): {e}")
        return None, refresh_token  # Keep old RT on network errors etc.

    except Exception as e:
        log.error(f"Unexpected error during token refresh: {e}", exc_info=True)
        return None, refresh_token


def test_api_call(access_token):
    """Makes a simple API call (/2/users/me) to test the access token."""
    if not access_token:
        log.warning("Cannot test API call without access token.")
        return False, None

    log.info("Testing current access token with /2/users/me...")
    api_url = f"{config.X_API_BASE_URL}/users/me"
    params = {"user.fields": "id"}
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        response = requests.get(
            api_url, headers=headers, params=params, timeout=config.TIMEOUT_API_TEST
        )
        if response.status_code == 200:
            log.info("Access token is valid.")
            user_data = response.json().get("data", {})
            return True, user_data.get("id")
        elif response.status_code == 401:
            log.warning(
                "Access token is invalid or expired (401 Unauthorized). Needs refresh."
            )
            return False, None
        elif response.status_code == 403:
            log.warning(
                f"Access token test failed (403 Forbidden). Might lack users.read scope or other issue: {response.text}"
            )
            return False, None  # Treat as invalid for now
        else:
            # Other errors (e.g., 5xx) might be temporary
            log.warning(
                f"Unexpected status code {response.status_code} when testing token: {response.text}"
            )
            return True, None  # Assume okay for now, but didn't get ID

    except requests.exceptions.Timeout:
        log.error(f"Network timeout testing access token.")
        return True, None  # Assume okay for now
    except requests.exceptions.RequestException as e:
        log.error(f"Network error testing access token: {e}")
        return True, None  # Assume okay for now
    except Exception as e:
        log.error(f"Unexpected error testing access token: {e}", exc_info=True)
        return True, None  # Assume okay for now
