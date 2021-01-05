import tweepy
import logging
import config
import lot

twitter_api = config.create_twitter_api()
street_view_key = config.get_street_view_api_key()


def main():
    nl = lot.NiceLot()

    nl.get_image(street_view_key)

    nl.prep_tweet(twitter_api)

    nl.post_tweet(twitter_api)

    nl.mark_as_tweeted()


if __name__ == '__main__':
    main()
