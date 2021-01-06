import yaml
import tweepy

# read in api keys
with open(r'api_keys.yaml') as file:
    keys = yaml.full_load(file)

# setup the authentication handler with the app's api key and secret
auth = tweepy.OAuthHandler(
    keys['app twitter']['key'], keys['app twitter']['secret'])

# get the authorization url from twitter and print it
try:
    redirect_url = auth.get_authorization_url()
    print(redirect_url)
except tweepy.TweepError:
    print('Error! Failed to get request token.')

# after authorizing the app, enter the verification pin
verifier = input('Verifier: ')

# get the access token for the posting account from twitter
auth.get_access_token(verifier)

# print the access token and secret
print("access token: ", auth.access_token)
print("access token secret: ", auth.access_token_secret)
