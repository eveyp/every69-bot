import sqlite3
import logging
from PIL import Image
import requests
from io import BytesIO
import config

QUERY = "SELECT * FROM only69 WHERE tweeted = 0 ORDER BY id LIMIT 1;"

svapi = "https://maps.googleapis.com/maps/api/streetview"

street_view_key = config.get_street_view_api_key()
twitter_api = config.create_twitter_api()
db_location = config.get_db_location()

st_abbs = ["rd", "dr", "st", "ave", "ln", "ct", "cir", "pl", "blvd", "trl", "av", "ter",
           "pkmy", "hwy", "rdg", "wy", "ext", "tr", "pt", "sq", "vlg", "hl", "terr",
           "hts", "holw", "bl", "aly", "ci", "tpke", "trce", "cl", "ests"]


class NiceLot(object):
    # on initialization query the db for an untweeted address
    def __init__(self, database=db_location):
        # connect to the db
        self.conn = sqlite3.connect(database)

        # execute the query
        cursor = self.conn.execute(QUERY)

        # gather the field names into a list
        keys = [k[0] for k in cursor.description]

        # set the address attribute as a dictionary with field name, value pairs
        self.address = dict(zip(keys, cursor.fetchone()))

        # grab the type of street from the last word of the street field
        street_type = self.address['street'].split(" ")[-1].lower()

        if street_type in st_abbs:
            self.address['street'] += "."

        logging.info("Got a lot: %s %s %s %s",
                     self.address['street'], self.address['city'], self.address['state'], self.address['zip'])

    def build_street_address(self):
        street_address = "%s %s %s %s %s" % (
            self.address['number'], self.address['street'], self.address['city'], self.address['state'], self.address['zip'])

        return(street_address)

    def is_address_usable(self, street_view_key=config.get_street_view_api_key()):
        return(self.is_address_complete() and self.is_address_in_street_view(street_view_key))

    def is_address_complete(self):
        return(bool(self.address['street'] and self.address['city'] and self.address['state']))

    def is_address_in_street_view(self, street_view_key):
        sv_meta_api = svapi + "/metadata"

        params = {'key': street_view_key,
                  'location': self.build_street_address()}

        res = requests.get(sv_meta_api, params)

        return(res.json()['status'] == "OK")

    # gets the image of the address from google street view
    def get_image(self, street_view_key=config.get_street_view_api_key()):
        # gather the street view api key, address, and image size for the api request
        params = dict(key=street_view_key,
                      location=self.build_street_address(),
                      size='1000x1000')

        # make the request to the street view api
        res = requests.get(svapi, params=params)

        # grab the image
        image = Image.open(BytesIO(res.content))

        # temporarily store the image
        self.tempimg = BytesIO()
        image.save(self.tempimg, format="jpeg")

        logging.info("Got image from Google")

    def prep_tweet(self, twitter_api=config.create_twitter_api()):
        filename = "%s.jpg" % self.address['id']
        self.image_id = twitter_api.media_upload(filename, file=self.tempimg)
        self.tweet_text = "{number} {street} {city}, {state}".format(
            number=self.address['number'],
            street=self.address['street'].title(),
            city=self.address['city'].title(),
            state=self.address['state'].upper())

        logging.info("Tweet text ready: %s", self.tweet_text)

    def post_tweet(self, twitter_api=config.create_twitter_api()):

        self.status_id = twitter_api.update_status(status=self.tweet_text,
                                                   media_ids=[
                                                       self.image_id.media_id_string],
                                                   lat=self.address['lat'],
                                                   lon=self.address['lon'])
        logging.info("Tweet posted")

    def mark_as_tweeted(self):
        self.conn.execute("UPDATE only69 SET tweeted = ? WHERE id = ?",
                          (self.status_id.id, self.address['id']))
        self.conn.commit()

        logging.info("Lot marked as tweeted")
