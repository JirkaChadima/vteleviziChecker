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
## - rss_base_link - link to your rss feed from vtelevizi.cz. You have to
##                   to include the token at the end of the URL.
## - rss_update_time - after how many minutes the feed will be refreshed
## - timeshift_from_GMT - due to the feedparser time parsing method, we have to
##                        shift every showtime we recieve in correct timezone.
## - tell_m_n_minutes_before - how many minutes before the start of the show
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
__date__ ="$Jan 10, 2011 8:36:24 PM$"
__version__ = "0.3"

database = []
rss_base_link = "http://vtelevizi.cz/export/rss/..."
rss_update_time = 5
timeshift_from_GMT = +2
tell_me_n_minutes_before = 5

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
        d = feedparser.parse(rss_base_link)
        for item in d['items'] :
            loctime = datetime.datetime(*time.localtime()[:6])
            showtime = shift_showtime(datetime.datetime(*item.date_parsed[:6]), timeshift_from_GMT)
            if loctime < showtime:
                s = Show(item.title, item.date_parsed)
                database.append(s)
    except Exception, e:
        logging.error(e)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.info("Starting v televizi checker %s" % __version__)

    counter = 0
    try:
        while True:
            if counter % rss_update_time == 0:
                refresh_rss()
                logging.info("There are currently %i records in your personal schedule..." % len(database))

            if len(database) > 0:
                try:
                    loctime = shift_loctime(datetime.datetime(*time.localtime()[:6]), tell_me_n_minutes_before)
                    showtime = shift_showtime(datetime.datetime(*database[0].timestamp[:6]), timeshift_from_GMT)

                    if loctime <= showtime:
                        del database[0]
                        logging.info("Wiping out %s, already running" % database[0].title)
                    if loctime > showtime:
                        n = pynotify.Notification(database[0].title, showtime.strftime("%d. %m. %Y %H:%M"), "video-display")
                        n.show()
                        logging.info("Showing %s" % database[0].title)
                except Exception, e:
                    logging.error("V televizi exception: ", e)
            counter += 1
            time.sleep(60)
    except KeyboardInterrupt, e:
        logging.info("Caught Ctrl+C, terminating...")

