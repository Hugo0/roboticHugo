# roboticHugo

Make an AI version of yourself!

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd roboticHugo
    ```
2.  **Create and activate a Python virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Install the local package:** (This makes imports from `src` work correctly)
    ```bash
    pip install -e .
    ```
5.  **Configure Environment Variables:**
    - Copy the example environment file:
      ```bash
      cp .env.example .env
      ```
    - Edit the `.env` file and fill in your credentials:
      - `TWITTER_CLIENT_ID`: Your X App Client ID.
      - `TWITTER_CLIENT_SECRET`: Your X App Client Secret (if applicable).
      - `TWITTER_REDIRECT_URI`: The exact callback URL registered in your X App settings (e.g., `http://127.0.0.1:5000/callback` for local auth).
      - `OPENAI_API_KEY`: Your OpenAI API Key.
      - Leave `TWITTER_ACCESS_TOKEN` and `TWITTER_REFRESH_TOKEN` blank for now.
      - If using an `http://` redirect URI, uncomment `OAUTHLIB_INSECURE_TRANSPORT=1`.
6.  **Initial Authentication:** Run the authentication script once to grant the bot permission and generate the initial user tokens. Follow the on-screen prompts (open URL, log in as the bot user, authorize, paste redirect URL back).
    ```bash
    # Make sure OAUTHLIB_INSECURE_TRANSPORT=1 is set if needed, e.g.:
    # export OAUTHLIB_INSECURE_TRANSPORT=1
    python src/authenticate.py
    ```
    This should automatically populate `TWITTER_ACCESS_TOKEN` and `TWITTER_REFRESH_TOKEN` in your `.env` file.

## Running the Bot

Make sure your virtual environment is activated (`source venv/bin/activate`).

There are two ways to run the bot:

1.  **Using the Run Script (Recommended):**

            - Make the script executable (only needs to be done once):
              ```bash
              chmod +x run.sh
              ```
            - Run the script:
              `bash

        ./run.sh
        `     or

    `bash
bash run.sh
`
    This script activates the virtual environment and starts the bot.

2.  **Manual Execution:**
    ```bash
    python -m src.main
    ```

The bot will run continuously, checking periodically if it needs to post a tweet. Stop it with `Ctrl+C`.

## Development

- **Testing Prompts:** To experiment with different OpenAI prompts without running the full bot loop, use the tester script:
  ```bash
  python scripts/prompt_tester.py
  ```
  (Edit the script to add/modify prompts.)
- **Running Unit Tests:**
  ```bash
  pytest
  ```

## Design goals:

see docs/system.md
