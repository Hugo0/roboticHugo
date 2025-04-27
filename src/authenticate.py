import os
import tweepy
import logging
import webbrowser
from dotenv import load_dotenv, set_key

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def save_tokens_to_dotenv(access_token, refresh_token):
    """Saves the access and refresh tokens to the .env file."""
    dotenv_path = ".env"
    try:
        logging.info(f"Attempting to save tokens to {dotenv_path}")
        # Use set_key to add/update variables in the .env file
        # It preserves existing variables and comments
        set_key(dotenv_path, "TWITTER_ACCESS_TOKEN", access_token)
        if refresh_token:
            set_key(dotenv_path, "TWITTER_REFRESH_TOKEN", refresh_token)
        logging.info("Successfully saved tokens to .env file.")
        return True
    except Exception as e:
        logging.error(f"Failed to save tokens to {dotenv_path}: {e}", exc_info=True)
        print(f"\nError: Could not automatically save tokens to {dotenv_path}.")
        print("Please add them manually:")
        print(f'TWITTER_ACCESS_TOKEN="{access_token}"')
        if refresh_token:
            print(f'TWITTER_REFRESH_TOKEN="{refresh_token}"')
        return False


def authenticate():
    # Load environment variables from .env file
    load_dotenv()
    logging.info("Loaded environment variables for authentication.")

    client_id = os.environ.get("TWITTER_CLIENT_ID")
    client_secret = os.environ.get("TWITTER_CLIENT_SECRET")
    redirect_uri = os.environ.get("TWITTER_REDIRECT_URI")

    if not all([client_id, client_secret, redirect_uri]):
        logging.error(
            "Missing required environment variables: TWITTER_CLIENT_ID, TWITTER_CLIENT_SECRET, TWITTER_REDIRECT_URI"
        )
        print(
            "Error: Ensure TWITTER_CLIENT_ID, TWITTER_CLIENT_SECRET, and TWITTER_REDIRECT_URI are set in your .env file."
        )
        return None  # Return None on failure

    # Define the scopes your application needs.
    scopes = ["tweet.read", "users.read", "tweet.write", "offline.access", "like.write"]
    logging.info(f"Requesting scopes: {', '.join(scopes)}")

    # Create the OAuth 2.0 handler with PKCE
    oauth2_user_handler = tweepy.OAuth2UserHandler(
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scopes,
        client_secret=client_secret,  # Client secret is required for token exchange
    )

    # --- Step 1: Get the authorization URL ---
    try:
        auth_url = oauth2_user_handler.get_authorization_url()
        logging.info(f"Authorization URL generated: {auth_url}")
        print("\n--- X Authentication ---")
        print(
            f"Using Redirect URI: {redirect_uri}"
        )  # Added to confirm which URI is being used
        print("1. Please open the following URL in your browser:")
        print(f"   {auth_url}")
        print("2. Log in as the target user (@roboticHugo) if prompted.")
        print("3. Authorize the application.")
        print(f"4. You will be redirected to: {redirect_uri}")
        print(
            "   Copy the *entire* URL from your browser's address bar after redirection."
        )

        # Optional: Try to automatically open the browser
        try:
            webbrowser.open(auth_url)
            logging.info("Attempted to open authorization URL in default browser.")
        except Exception as e:
            logging.warning(
                f"Could not automatically open browser: {e}. Please open the URL manually."
            )

        # --- Step 2: Get the access token ---
        redirect_response_url = input(
            "\n5. Paste the full redirect URL here and press Enter:\n> "
        )
        logging.info(f"Received redirect URL from user.")

        if not redirect_response_url or redirect_uri not in redirect_response_url:
            logging.error(
                "Invalid redirect URL pasted. Expected base: %s", redirect_uri
            )
            print(
                f"Error: The pasted URL does not seem valid or doesn't contain the expected base: {redirect_uri}"
            )
            return None

        # Fetch the access token
        logging.info("Fetching access and refresh tokens...")
        access_token_data = oauth2_user_handler.fetch_token(redirect_response_url)

        access_token = access_token_data.get("access_token")
        refresh_token = access_token_data.get("refresh_token")
        expires_in = access_token_data.get(
            "expires_in"
        )  # Typically 7200 seconds (2 hours)

        if not access_token:
            logging.error(
                "Failed to fetch access token. Data received: %s", access_token_data
            )
            print("Error: Could not retrieve access token from X.")
            return None

        logging.info(f"Successfully obtained Access Token (expires in {expires_in}s).")
        if refresh_token:
            logging.info("Successfully obtained Refresh Token.")
        else:
            logging.warning(
                "Refresh Token was NOT obtained. Ensure 'offline.access' scope was requested and granted."
            )

        print("\n--- Authentication Successful ---")
        print(f"Access Token (valid for ~{expires_in // 60} minutes):")
        print(access_token)
        print("\nRefresh Token:")
        print(refresh_token if refresh_token else "N/A")
        print("\n--- IMPORTANT ---")
        print("Add or update the following lines in your .env file:")
        print(f'TWITTER_ACCESS_TOKEN="{access_token}"')
        if refresh_token:
            print(f'TWITTER_REFRESH_TOKEN="{refresh_token}"')
        print("\nAfter updating .env, you can run main.py to post a tweet.")

        # Save tokens automatically
        if save_tokens_to_dotenv(access_token, refresh_token):
            print("Tokens automatically saved to .env file.")
        else:
            print("Failed to automatically save tokens. Please update .env manually.")

        # Return the configured handler instance
        return oauth2_user_handler

    except tweepy.errors.TweepyException as e:
        logging.error(f"Tweepy error during authentication: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(
                f"Error during authentication. Status code: {e.response.status_code}. Reason: {e.response.reason}"
            )
            try:
                print(f"Response text: {e.response.text}")
            except Exception:
                pass
        else:
            print(f"An error occurred during authentication: {e}")
        return None  # Return None on failure
    except Exception as e:
        logging.error(
            f"An unexpected error occurred during authentication: {e}", exc_info=True
        )
        print(f"An unexpected error occurred: {e}")
        return None  # Return None on failure


if __name__ == "__main__":
    # Run authenticate if script is executed directly, but don't exit script if imported
    returned_handler = authenticate()
    if returned_handler:
        print("\nauthenticate.py executed successfully and tokens saved (if possible).")
    else:
        print("\nauthenticate.py failed.")
        # Optional: exit if run directly and failed
        # import sys
        # sys.exit(1)
