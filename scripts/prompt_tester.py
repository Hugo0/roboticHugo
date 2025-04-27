"""Script for testing and developing prompts for ai."""

import os
import sys
import logging  # Import logging

# Add src directory to path to allow importing modules
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.append(SRC_DIR)

import ai

# --- Setup Logging for the Tester ---
# This will show DEBUG messages from imported modules like 'ai'
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)  # Logger for this script itself (optional)
# --- End Logging Setup ---


def main():
    log.info("--- Prompt Tester --- (Uses real OpenAI API Calls!) ---")

    # 1. Initialize REAL OpenAI Client
    openai_client = ai.initialize_openai_client()
    if not openai_client:
        print("Failed to initialize OpenAI client. Check API Key.")
        return

    # 2. Define Prompts to Test
    prompts_to_test = [
        f"Think about a few tweets or shitposts that you would like to write. Then find the one that would perform best on twitter. Your response should include the tokens <final_tweet> before the final tweet text.",
        # f"Generate one short, insightful, and slightly provocative tweet (less than 280 characters) about the future of AI, human-computer interaction, or software development. Emulate the style of Paul Graham or Naval Ravikant.",
        # f"Write a tweet under 280 characters offering a contrarian viewpoint on the current state of prompt engineering, in the style of Paul Graham.",
    ]

    # 3. Loop through prompts and generate tweets
    for i, prompt in enumerate(prompts_to_test):
        print(f"\n--- Testing Prompt {i+1} ---")
        print(f"Prompt: {prompt}")

        # Call generate_smart_tweet with the specific prompt
        generated_tweet = ai.generate_smart_tweet(openai_client, prompt_override=prompt)

        print(f"Generated Tweet {i+1}:")
        if generated_tweet:
            print()
            print("\033[32m" + generated_tweet + "\033[0m")  # Print in green color
            print()

        else:
            print("-> Failed to generate tweet for this prompt.")

    print("\n--- Prompt Testing Complete ---")


if __name__ == "__main__":
    main()
