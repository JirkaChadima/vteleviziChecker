#!/usr/bin/python

################################################################################
##
## vteleviziChecker
## -----------------------------------------------------------------------------
## This short python script is meant to serve as an 'integrated' notifier of
## TV shows in Ubuntu with libnotify. It is using the capabilites of web
## application vtelevizi.cz and its short personal RSS channel.
##
## For RSS channel parsing, the script uses feedparser (http://feedparser.org).
##
##
## Dependencies
## ------------
## For correct usage, you have to have python-notify and python-feedparser
## packages installed. They are both available in standard repositories.
##
## Usage
## -----
## There are three configuration variables.
## - RSS_BASE_LINK - link to your rss feed from vtelevizi.cz. You have to
##                   to include the token at the end of the URL.
## - RSS_UPDATE_TIME - after how many minutes the feed will be refreshed
## - TIMESHIFT_FROM_GMT - due to the feedparser time parsing method, we have to
##                        shift every showtime we recieve in correct timezone.
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


import time
import datetime
import pynotify
import feedparser
import logging


__author__="Jirka Chadima"
__date__ ="$Jan 12, 2011 0:36:24 PM$"
__version__ = "0.4"

database = []

LOGFILE = "vtelevizichecker.log"
BASE_URL = "http://vtelevizi.cz/"
DETAIL_SLUG = "detail/"


RSS_BASE_LINK = BASE_URL+"export/rss/..."
RSS_UPDATE_TIME = 5
TIMESHIFT_FROM_GMT = +2
TELL_ME_N_MINUTES_BEFORE = 2

class Show:
    """Data unit for a single broadcast of a TV show"""
    def __init__(self, title, timestamp):
        """Just data initialization"""
        self.title = title
        self.timestamp = timestamp


def shift_showtime(showtime, hours_shift):
    """Adds given hours to a showtime"""
    return showtime + datetime.timedelta(hours=hours_shift)

def shift_loctime(loctime, minutes_shift):
    """Adds given minutes to a loctime"""
    return loctime + datetime.timedelta(minutes=minutes_shift)

def refresh_rss():
    """Refreshes RSS feed and updates 'database' of TV shows. Does not append
    tv shows that are in progress."""
    logging.info("Refreshing RSS...")
    global database
    database = []
    try:
        d = feedparser.parse(RSS_BASE_LINK)
        for item in d['items'] :
            loctime = datetime.datetime(*time.localtime()[:6])
            showtime = shift_showtime(datetime.datetime(*item.date_parsed[:6]), TIMESHIFT_FROM_GMT)
            if loctime < showtime:
                s = Show(item.title, item.date_parsed)
                database.append(s)
    except Exception, e:
        logging.error(e)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, filename=LOGFILE)
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
                    showtime = shift_showtime(datetime.datetime(*database[0].timestamp[:6]), TIMESHIFT_FROM_GMT)

                    if showtime < datetime.datetime(*time.localtime()[:6]):
                        logging.info("Wiping out %s, already running" % database[0].title)
                        del database[0]
                    elif loctime > showtime:
                        n = pynotify.Notification(database[0].title, showtime.strftime("%d. %m. %Y %H:%M"), "video-display")
                        n.show()
                        logging.info("Showing %s" % database[0].title)
                except Exception, e:
                    logging.error("V televizi exception: ", e)
            counter += 1
            time.sleep(60)
    except KeyboardInterrupt, e:
        logging.info("Caught Ctrl+C, terminating...")

