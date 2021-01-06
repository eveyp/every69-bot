import tweepy
import logging
import config
import lot


def main():
    try:
        nl = lot.NiceLot()
    except Exception as e:
        logging.exception("Lot not created")
        raise e

    try:
        nl.get_image(lot.street_view_key)
    except Exception as e:
        logging.exception("Error while getting image from Google")
        raise e

    try:
        nl.prep_tweet(lot.twitter_api)
    except Exception as e:
        logging.exception("Error while preparing tweet")
        raise e

    try:
        nl.post_tweet(lot.twitter_api)
    except Exception as e:
        logging.exception("Error while posting tweet")

    try:
        nl.mark_as_tweeted()
    except Exception as e:
        logging.exception("Error while marking lot tweeted")
        raise e


if __name__ == '__main__':
    main()
