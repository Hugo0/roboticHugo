# if you have a second account that you want to tweet from, here is how to get the access tokens:

import tweepy
import dotenv
import os

# Load environment variables
dotenv.load_dotenv(".env")
CONSUMER_KEY = os.getenv("TWITTER_V1_API_KEY")
CONSUMER_SECRET = os.getenv("TWITTER_V1_API_KEY_SECRET")
ACCESS_TOKEN = os.getenv("TWITTER_V1_ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("TWITTER_V1_ACCESS_TOKEN_SECRET")
BEARER_TOKEN = os.getenv("TWITTER_V1_BEARER_TOKEN")

# Authenticate to Twitter
auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

# Create API object
api = tweepy.API(auth)

# Create a tweet
# THIS MAKES IT WITH THE WRONG ACCOUNT - WE WANT TO USE THE BOT ACCOUNT
# api.update_status("Hello World 🤖 - Testing Twitter API")

try:
    redirect_url = auth.get_authorization_url()
except tweepy.TweepError:
    print('Error! Failed to get request token.')

print(f"NAVIGATE TO: {redirect_url}")

verifier = input('copy paste the oauth_verifier from the url: ')

try:
    token, secret = auth.get_access_token(verifier)
except tweepy.TweepError:
    print('Error! Failed to get access token.')

print(f"ACCESS_TOKEN = {token}")
print(f"ACCESS_TOKEN_SECRET = {secret}")

print("\nNow you can use the access tokens to authenticate to Twitter")