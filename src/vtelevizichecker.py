#!/usr/bin/python
# -*- coding: utf-8 -*-

################################################################################
##
## vteleviziChecker
## -----------------------------------------------------------------------------
## This short python script is meant to serve as an 'integrated' notifier of
## TV shows in Ubuntu with libnotify. It is using the capabilites of web
## application vtelevizi.cz and its short personal RSS channel.
##
##
## Dependencies
## ------------
## For correct usage, you have to have python-notify package installed.
## It is available in standard repositories.
##
## Usage
## -----
##   python vtelevizichecker.py username rsshash
## where username is your vtelevizi.cz username and rsshash is a secret part
## of your RSS url.
##
## There are three configuration variables.
## - RSS_UPDATE_TIME - after how many minutes the feed will be refreshed
## - TELL_ME_N_MINUTES_BEFORE - how many minutes before the start of the show
##                             the notification should be displayed. It is then
##                             shown every minute until the start of the show.
##
## After configuration, the script runs in an infinite loop. Every minute, it
## checkes whether some show is starting in n minutes. If yes, a notification
## is shown. It is then shown every minute until the show starts. Every m
## minutes, RSS feed is checked again to include updates. Items are stored
## in local list, every time RSS is refreshed, the list is deleted.
##
##
## Author
## ------
## Jirka Chadima, chadima.jiri@gmail.com, 01/2010
##
## License
## -------
## MIT, feel free to use and improve the code
################################################################################

### imports

import time
import sys
from HTMLParser import HTMLParser
import datetime
import logging
import pynotify
import urllib
from xml.etree import ElementTree

### credentials

__author__ = "Jirka Chadima"
__date__ = "$Thu Jan 20 16:45:26 CET 2011$"
__version__ = "0.5"

### basic configuration

LOG_FILENAME = "vtelevizi.log"
BASE_URL = "http://vtelevizi.cz/"
DETAIL_SLUG = "detail/"
DEBUG = False

### user configuration

RSS_BASE_LINK = BASE_URL + "export/rss/"
RSS_UPDATE_TIME = 5
TELL_ME_N_MINUTES_BEFORE = 2

### global structures

database = {}

### helper classes

class Show:
    """Data unit for a single broadcast of a TV show"""
    def __init__(self, title, timestamp, id, channel):
        """Just data initialization"""
        self.title = title
        self.timestamp = timestamp
        self.id = id
        self.channel = channel

class ChannelRetriever(HTMLParser):
    """
    Custom HTML parser that is used to get a channel information from a detail
    page for each show. If the RSS channel had such information, ot would be
    much nicer.
    """

    channel = None
    in_info = False
    in_info_p = False
    fetch_channel = False

    def handle_data(self, data):
        if self.fetch_channel:
            self.channel = data.strip()

        if self.in_info_p and data == "kanál:": # ugly, but necessary
            self.fetch_channel = True

    def handle_starttag(self, tag, attrs):
        if tag == 'div' and attrs[0][0] == 'class' and attrs[0][1] == 'infoItem':
            self.in_info = True

        if tag == 'p' and self.in_info:
            self.in_info_p = True

    def handle_endtag(self, tag):
        if tag == 'div':
            self.in_info = False
        if tag == 'p':
            self.in_info_p = False
            self.fetch_channel = False

    def get_channel(self):
        return self.channel

### helper functions

def shift_loctime(loctime, minutes_shift):
    """Adds given minutes to a loctime"""
    return loctime + datetime.timedelta(minutes=minutes_shift)

def refresh_rss(rss_link):
    """Refreshes RSS feed and updates 'database' of TV shows. Does not append
    tv shows that are in progress."""
    logging.info("Refreshing RSS on %s..." % rss_link)
    global database
    ids = {}

    try:
        feed = urllib.urlopen(rss_link)
        tree = ElementTree.XML(feed.read())
        feed.close()
        items = tree.find('channel').findall('item')
        loctime = datetime.datetime(*time.localtime()[:6])

        for item in items: # gather current ids in RSS
            ids[item.find('link').text.split('=')[1]] = None

        # delete shows deleted in RSS feed
        for sid in database.keys():
            if sid not in ids: # show was removed from RSS feed, delete locally
                del database[sid]

        # append show added to RSS feed
        for item in items:
            id = item.find('link').text.split('=')[1]
            if id in database: # skip existing items
                continue

            title = item.find('title').text
            date_parsed = datetime.datetime(* time.strptime(' '.join(item.find('pubDate').text.split(' ')[:-1]), "%a, %d %b %Y %H:%M:%S")[:6])

            try:
                if loctime < date_parsed:
                    logging.debug("Getting channel...")
                    f = urllib.urlopen(BASE_URL + DETAIL_SLUG + id)
                    retriever = ChannelRetriever()
                    retriever.feed(f.read())
                    channel = retriever.get_channel()
                    f.close()
                    retriever.close()
                    logging.debug("Got channel...")
                    database[id] = Show(title, date_parsed, id, channel)
            except Exception, e:
                logging.error("Can't get channel...")
    
    except Exception, e:
        logging.error("RSS feed error: %s", e)

### main loop

if __name__ == "__main__":
    if DEBUG:
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s:%(levelname)s:%(message)s')
    else:
        logging.basicConfig(filename=LOG_FILENAME,
                            level=logging.INFO,
                            format='%(asctime)s:%(levelname)s:%(message)s')

    
    logging.info("Starting v televizi checker %s" % __version__)

    # check libnotify capabilities
    if not pynotify.init("icon-summary-body"):
        logging.fatal("Your libnotify does not support required format.")
        sys.exit(1)

    # check arguments (username + secret key)
    if len(sys.argv) < 3:
        logging.fatal("Not enough arguments! Sample usage: python vtelevizi.py username hash")
        sys.exit(1)

    uname = sys.argv[1]
    hash = sys.argv[2]
    rss_link = RSS_BASE_LINK + uname + '/' + hash

    counter = 0
    db = database
    try:
        while True:
            if counter == 0 or counter % RSS_UPDATE_TIME == 0:
                refresh_rss(rss_link)
                db = sorted(database.values(), key=lambda show: show.timestamp)
                logging.info("There are currently %i records in your personal schedule..." % len(database))

            if len(db) > 0:
                try:
                    loctime = shift_loctime(datetime.datetime(*time.localtime()[:6]), TELL_ME_N_MINUTES_BEFORE)
                    now = datetime.datetime(*time.localtime()[:6])
                    count = -1
                    for show in db :
                        count += 1
                        if show.timestamp < now :
                            logging.info("Wiping out %s, already running" % show.title)
                            del database[show.id]
                            del db[count]
                        elif show.timestamp < loctime :
                            n = pynotify.Notification(show.title, show.channel + ", " + show.timestamp.strftime("%d. %m. %Y %H:%M"), "video-display")
                            n.show()
                            logging.info("Showing %s" % show.title)
                        else :
                            break


                except Exception, e:
                    logging.error("V televizi exception: ", e)
            counter += 1
            time.sleep(60)
    except KeyboardInterrupt, e:
        logging.info("Caught Ctrl+C, terminating...")
        sys.exit(0)

