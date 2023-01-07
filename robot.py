import tweepy
import dotenv
import os
import requests
import json
import time
import random
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables
dotenv.load_dotenv(".env")
CONSUMER_KEY = os.getenv("TWITTER_API_KEY")
CONSUMER_SECRET = os.getenv("TWITTER_API_KEY_SECRET")
BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN") # Main account
ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET") # Main account
CLIENT_ACCESS_TOKEN = os.getenv("TWITTER_CLIENT_ACCESS_TOKEN") # Client 
CLIENT_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_CLIENT_ACCESS_TOKEN_SECRET") # Client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Authenticate to Twitter
auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
# auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET) # main account
auth.set_access_token(CLIENT_ACCESS_TOKEN, CLIENT_ACCESS_TOKEN_SECRET) # bot account

# Create API object
api = tweepy.API(auth)

# # MAKE TEST TWEET
# api.update_status("Hello World 🤖 - Testing Twitter API")


def generate_response(tweet):
    """Generate an AI response to a tweet"""

    tweeter_name = tweet.user.name
    text = tweet.full_text
    prompt = f"""You are an exceptionally smart person, using twitter. Your fields of interest are AI, Blockchain, and software development in general. You generally have a cheery attitude on Twitter. Someone with the name of '{tweeter_name}' tweeted the following thing: \n<BEGIN TWEET>{text}<END TWEET>\nGenerate a snarky but supportive, intelligent response. Do not use hashtags. \n\n"""

    # get OpenAI response
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {OPENAI_API_KEY}',
    }
    json_data = {
        'model': 'text-davinci-003',
        'prompt': prompt,
        'max_tokens': 200,
        'temperature': 1.0,
    }
    response = requests.post('https://api.openai.com/v1/completions', headers=headers, json=json_data, verify=False)
    try:
        response_json = json.loads(response.text)
    except Exception as e:
        print(e)
        raise Exception("OpenAI API error")


    try:
        text = response_json['choices'][0]['text']
        text = sanitize_ai_response(text)
    except Exception as e:
        print(e)
        print(response_json)
        raise Exception("OpenAI API error")
    return text


def sanitize_ai_response(text):
    """Sanitize the AI response to remove any unwanted text"""

    if "\n\n" in text:
        text = text.split("\n\n")[1]

    # if text starts with " and ends with ", remove the quotes
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    # check again
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    # remove starting or ending quotes
    if text.startswith('"'):
        text = text[1:]
    if text.endswith('"'):
        text = text[:-1]
    
    return text


def is_tweet_valid(tweet):
    """Checks if a tweet is valid to reply to.
    
    Rules to check:
    - should be a top level tweet
    - should not be a retweet, quote tweet, or reply
    - should not have been replied to already by the bot
    - should not include a link, or image or any other media
    """

    # check if tweet is a top level tweet
    if tweet.in_reply_to_status_id is not None:
        return False
    # check if tweet is a retweet, quote tweet, or reply
    if 'RT @' in tweet.full_text or tweet.is_quote_status:
        return False
    # check if tweet has been replied to already by the bot
    if str(tweet.id) in get_replied_to_tweets():
        return False
    # check if tweet has a link, image, or any other media
    if tweet.entities['urls'] or 'media' in tweet.entities:
        return False
    # exempt @roboticHugo tweets from being replied to
    if tweet.user.screen_name == "roboticHugo":
        return False

    return True


def get_replied_to_tweets():
    """Loads the replied to tweets from the file"""
    if os.path.exists("replied_to_tweets.txt"):
        with open("replied_to_tweets.txt", "r") as f:
            replied_to_tweets = f.read().splitlines()
    else:
        replied_to_tweets = []
    return replied_to_tweets


def add_replied_to_tweet(tweet_id):
    """Adds a tweet id to a new line in the replied to tweets file"""
    with open("replied_to_tweets.txt", "a") as f:
        f.write(f"{tweet_id}\n")


def main():
    """Main Loop. Gets tweets and then replies to them
    
        To not double reply, we keep track of the tweet ids we have replied to in a file
    """
    minutes_passed = 0
    while True:
        # get tweets
        tweets = api.home_timeline(tweet_mode="extended", count=100)
        invalid_tweet_count = 0
        print(f"Fetched {len(tweets)} tweets")
        for tweet in tweets:
            # print(f"Checking tweet: {tweet.id}... (url: https://twitter.com/{tweet.user.screen_name}/status/{tweet.id})")
            # check if tweet is valid
            if not is_tweet_valid(tweet):
                invalid_tweet_count += 1
                continue

            try:

                # print to log
                print(f"==================== Tweet ====================")
                print(f"{tweet.full_text}")
                print(f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}")
                print(f"==================== Response ====================")
                # generate response
                response = generate_response(tweet)
                print(f"{response}")
                print(f"==================== End ====================")

                # reply to tweet
                response_tweet = api.update_status(response, in_reply_to_status_id=tweet.id, auto_populate_reply_metadata=True)

                # like our own response tweet
                api.create_favorite(response_tweet.id)

                # add tweet id to replied to tweets
                add_replied_to_tweet(tweet.id)

                # like the tweet
                api.create_favorite(tweet.id)

            except Exception as e:
                print(e)
                print("Error, continuing...")
                continue

            # wait random amount of time to avoid rate limiting (5 - 15 seconds)
            time_to_wait = random.randint(60, 240)
            print(f"Waiting {time_to_wait} seconds before checking for new tweets...")
            time.sleep(time_to_wait)
        
        # wait 5 minutes before checking for new tweets
        print(f"Checked {len(tweets)} tweets, {invalid_tweet_count} were invalid tweets. (Replies, retweets, or already replied to.)")
        print("Waiting 5 minutes before checking for new tweets...\n")
        time.sleep(60 * 5)
        minutes_passed += 5

        # if 3 hours have passed, make a tweet
        if minutes_passed >= 360:
            minutes_passed = 0
            try:
                tweet = generate_guru_tweet()
                status_tweet = api.update_status(tweet)
                api.create_favorite(status_tweet.id)
            except Exception as e:
                print(e)
                print("Error, continuing...")
                continue
        

def generate_guru_tweet():
    """Generates a tweet to post to the twitter account"""

    adjectives = ['insightful', 'smart', 'intelligent', 'novel', 'cool', 'happy', 'pessimistic', 'innovative', 'teaching', 'original']
    prompt = f"""You are an exceptionally smart person, using twitter. You have {random.randint(500, 50000)} followers and have written {random.randint(100, 3000)} tweets.
Your fields of interest are AI, Blockchain, Software Development, Fullstack, Startups, Health, Fitness, and other stuff like that.
Your tweets are often full of wisdom and short. You do not use hashtags.
Generate a {random.choice(adjectives)} tweet that you would post to your twitter account. Do not use Hashtags."""

    # get OpenAI response
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {OPENAI_API_KEY}',
    }
    # get random seed
    seed = random.randint(0, 1000000000)
    json_data = {
        'model': 'text-davinci-003',
        'prompt': prompt,
        'max_tokens': 300,
        'temperature': 1.0,
    }
    response = requests.post('https://api.openai.com/v1/completions', headers=headers, json=json_data, verify=False)
    try:
        response_json = json.loads(response.text)
    except Exception as e:
        print(e)
        raise Exception("OpenAI API error")


    text = response_json['choices'][0]['text']
    text = sanitize_ai_response(text)
    return text



if __name__ == "__main__":
    main()