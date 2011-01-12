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
## There are three configuration variables.
## - RSS_BASE_LINK - link to your rss feed from vtelevizi.cz. You have to
##                   to include the token at the end of the URL.
## - RSS_UPDATE_TIME - after how many minutes the feed will be refreshed
## - TELL_ME_N_MINUTES_BEFORE - how many minutes before the start of the show
##                             the notification should be displayed
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
import datetime
import pynotify
import logging
import urllib
from xml.etree import ElementTree
from HTMLParser import HTMLParser

### credentials

__author__="Jirka Chadima"
__date__ ="$Jan 12, 2011 21:28:30 PM$"
__version__ = "0.4"

### basic configuration

#LOG_FILENAME = "vtelevizi.log"
BASE_URL = "http://vtelevizi.cz/"
DETAIL_SLUG = "detail/"

### user configuration

RSS_BASE_LINK = BASE_URL+"export/rss/..."
RSS_UPDATE_TIME = 5
TELL_ME_N_MINUTES_BEFORE = 2

### global structures

database = []
database_keys = {}

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

def refresh_rss():
    """Refreshes RSS feed and updates 'database' of TV shows. Does not append
    tv shows that are in progress."""
    logging.info("Refreshing RSS...")
    global database, database_keys

    try:
        feed = urllib.urlopen(RSS_BASE_LINK)
        tree = ElementTree.XML(feed.read())
        feed.close()
        items = tree.find('channel').findall('item')
        loctime = datetime.datetime(*time.localtime()[:6])

        for item in items :
            title = item.find('title').text
            id = item.find('link').text.split('=')[1]
            date_parsed = datetime.datetime( *time.strptime(' '.join( item.find('pubDate').text.split(' ')[:-1] ), "%a, %d %b %Y %H:%M:%S")[:6] )

            if id in database_keys: # skip existing items
                continue

            if loctime < date_parsed:

                logging.debug("Getting channel...")
                f = urllib.urlopen(BASE_URL + DETAIL_SLUG + id)
                retriever = ChannelRetriever()
                retriever.feed(f.read())
                channel = retriever.get_channel()
                f.close()
                retriever.close()
                logging.debug("Got channel...")

                s = Show(title, date_parsed, id, channel)
                database.append(s)
                database_keys[id] = None
    except Exception, e:
        logging.error(e)

### main loop

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    logging.info("Starting v televizi checker %s" % __version__)

    counter = 0
    try:
        while True:
            if counter % RSS_UPDATE_TIME == 0:
                refresh_rss()
                logging.info("There are currently %i records in your personal schedule..." % len(database))

            if len(database) > 0:
                try:
                    loctime = shift_loctime(datetime.datetime(*time.localtime()[:6]), TELL_ME_N_MINUTES_BEFORE)

                    if database[0].timestamp < datetime.datetime(*time.localtime()[:6]):
                        logging.info("Wiping out %s, already running" % database[0].title)
                        del database_keys[database[0].id]
                        del database[0]
                    elif loctime > database[0].timestamp:
                        n = pynotify.Notification(database[0].title, database[0].channel+", "+database[0].timestamp.strftime("%d. %m. %Y %H:%M"), "video-display")
                        n.show()
                        logging.info("Showing %s" % database[0].title)
                except Exception, e:
                    logging.error("V televizi exception: ", e)
            counter += 1
            time.sleep(60)
    except KeyboardInterrupt, e:
        logging.info("Caught Ctrl+C, terminating...")

