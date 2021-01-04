import sqlite3
import logging
from PIL import Image
import requests
from io import BytesIO
import config

QUERY = "SELECT * FROM portland_test WHERE tweeted = 0 ORDER BY id LIMIT 1;"

svapi = "https://maps.googleapis.com/maps/api/streetview"

street_view_key = config.get_street_view_api_key()
twitter_api = config.create_twitter_api()

class NiceLot(object):
    # on initialization query the db for an untweeted address
    def __init__(self, database = 'addresses.db'):
        # connect to the db
        self.conn = sqlite3.connect(database)

        # execute the query
        cursor = self.conn.execute(QUERY)

        # gather the field names into a list
        keys = [k[0] for k in cursor.description]

        # set the address attribute as a dictionary with field name, value pairs
        self.address = dict(zip(keys, cursor.fetchone()))

    # gets the image of the address from google street view
    def get_image(self, street_view_key=config.get_street_view_api_key()):
        # concatenate the address
        self.street_address = "%s %s %s %s %s" % (self.address['number'], self.address['street'], self.address['city'], self.address['region'], self.address['postcode'])

        # gather the street view api key, address, and image size for the api request
        params = dict(key = street_view_key,
                      location = self.street_address,
                      size = '1000x1000')
        
        # make the request to the street view api
        res = requests.get(svapi, params=params)

        # grab the image
        image = Image.open(BytesIO(res.content))

        # temporarily store the image
        self.tempimg = BytesIO()
        image.save(self.tempimg, format="jpeg")

    def upload_image(self, twitter_api = config.create_twitter_api()): 
        filename = "%s.jpg" % self.address['id']
        self.image_id = twitter_api.media_upload(filename, file=self.tempimg)
         
    def post_tweet(self, twitter_api = config.create_twitter_api()):
        text = self.street_address.title().strip()
        text = " ".join(text.split())
        self.status_id = twitter_api.update_status(status=text,
                                  media_ids=[self.image_id.media_id_string],
                                  lat=self.address['lat'],
                                  lon=self.address['lon'])
    
    def mark_as_tweeted(self):
        self.conn.execute("UPDATE portland_test SET tweeted = ? WHERE id = ?", (self.status_id.id, self.address['id']))
        self.conn.commit()




