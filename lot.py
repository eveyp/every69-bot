import sqlite3
import logging
import requests
import googlemaps
from PIL import Image
from io import BytesIO
import config

# url for the street view api
svapi = "https://maps.googleapis.com/maps/api/streetview"
# grab the google api key
google_key = config.get_street_view_api_key()
# set up the googls maps api
gmaps = googlemaps.Client(key=google_key)
# set up the twitter api
twitter_api = config.create_twitter_api()
# grab the database location
db_location = config.get_db_location()


class NiceLot(object):
    # on initialization query the db for an untweeted address
    def __init__(self, database=db_location, id=None):
        # connect to the db
        self.conn = sqlite3.connect(database)

        QUERY = "SELECT * FROM only69 WHERE {} = ? ORDER BY RANDOM() LIMIT 1;"

        if id:
            # if an id is specified, check the id field for the supplied id (WHERE id = <id>)
            QUERY = QUERY.format("id")
            value = id
        else:
            # otherwise grab one that hasn't been tweeted (WHERE tweeted = 0)
            QUERY = QUERY.format("tweeted")
            value = "0"

        # execute the query
        cursor = self.conn.execute(QUERY, value)

        # gather the field names into a list
        keys = [k[0] for k in cursor.description]

        # set the address attribute as a dictionary with field name, value pairs
        self.address = dict(zip(keys, cursor.fetchone()))

        # check if the address has all the fields it needs
        if self.is_address_complete():
            # if it does, send it to google to standardize address format
            res = gmaps.geocode(self.build_street_address(), region="us")
        else:
            # if it doesn't, try to reverse geocode
            # grab the lat and lon to send to google
            latlon = (self.address['lat'], self.address['lon'])
            try:
                # send it to google and limit it to results with street address precision only
                res = gmaps.reverse_geocode(
                    latlon, location_type="ROOFTOP", result_type="street_address")
            except:
                # if this errors out, just toss the address and start over
                self.bad_address()

        # keep the original address dict around
        self.orig_address = self.address.copy()
        # parse the response from google, getting the address components
        # comes back as a list of address component dicts
        for part in res[0]['address_components']:
            # find the one corresponding to street number
            if "street_number" in part['types']:
                # update the street number
                self.address['number'] = part['long_name']

            # find the one corresponding to street name
            if "route" in part['types']:
                # update the street name
                self.address['street'] = part['long_name']

            # find the one corresponding to city
            if "locality" in part['types']:
                # update the city name
                self.address['city'] = part['short_name']

            # find the one corresponding to state
            if "administrative_area_level_1" in part['types']:
                # update the state
                self.address['state'] = part['long_name']

            # find the one corresponding to zipcode
            if "postal_code" in part['types']:
                # update the zipcode
                self.address['zip'] = part['long_name']

        # if google gave us something with a street number that's not 69, throw it away and start over
        if self.address['number'] != "69":
            self.bad_address()

        # log the good address we got
        logging.info("Got a lot: " + self.build_street_address())

    # puts in address in one string: 'number street city, state zipcode'
    def build_street_address(self, address="address"):
        # decide which address dict to use (by default 'address')
        address_dict = getattr(self, address)
        # assemble the address string
        street_address = "%s %s %s, %s %s" % (
            address_dict['number'], address_dict['street'], address_dict['city'], address_dict['state'], address_dict['zip'])

        return(street_address)

    # checks if the address has the required fields: street, city, & state
    def is_address_complete(self):
        # returns true if they are all non-empty
        return(bool(self.address['street'] and self.address['city'] and self.address['state']))

    # checks if street view has an image for the lot
    def is_address_in_street_view(self, street_view_key=google_key):
        sv_meta_api = svapi + "/metadata"

        params = {'key': google_key,
                  'location': self.build_street_address()}

        res = requests.get(sv_meta_api, params)

        return(res.json()['status'] == "OK")

    # gets the image of the lot from google street view
    def get_image(self, street_view_key=google_key):
        # if street view doesn't have an image for the lot, toss it and start over
        if not self.is_address_in_street_view(street_view_key):
            self.bad_address()

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

    def prep_tweet(self, twitter_api=twitter_api):
        filename = "%s.jpg" % self.address['id']
        self.image_id = twitter_api.media_upload(filename, file=self.tempimg)
        self.tweet_text = "{number} {street} {city}, {state}".format(
            number=self.address['number'],
            street=self.address['street'],
            city=self.address['city'],
            state=self.address['state'])

        logging.info("Tweet text ready: %s", self.tweet_text)

    def post_tweet(self, twitter_api=twitter_api):

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

    def bad_address(self):
        # mark the bad address so we don't try it again (set tweeted to -1)
        self.conn.execute(
            "UPDATE only69 SET tweeted = -1 WHERE id = ?", (self.address['id'],))
        self.conn.commit()

        # make a note of the bad address in the log
        logging.info("Bad address, trying again: " +
                     self.build_street_address("orig_address"))

        # start over with a new address
        self.__init__()
