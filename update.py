#!/usr/bin/env python

# Config
import logging
import requests
import re
import os
import readability
from readability.api import ResponseError
from BeautifulSoup import BeautifulSoup as Soup

urlfinder = re.compile(r"(https?://[^ )]+)")

logger = logging.getLogger(__file__)
logger.setLevel(logging.DEBUG)
filepath = os.path.join(os.path.dirname(__file__), 'readability.log')
fh = logging.FileHandler(filepath)
fh.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)


def get_article_urls_from_twitter_favourites(username, n=20):
    """
    Return a list of article URLs extracted from a user's twitter favourites
    """
    urls = []

    logger.info("Fetching Twitter favourite articles for %s", username)
    twitter_url = 'https://api.twitter.com/1/favorites.json?count=%d&screen_name=%s' % (
        n, username)
    response = requests.get(twitter_url)

    if response.status_code != 200:
        return []

    for tweet in response.json:
        text = tweet['text']
        # Look for a link
        match = urlfinder.search(text)
        if not match:
            continue
        # Check link is an article
        redirect_url = match.groups()[0]
        url_resp = requests.get(redirect_url)
        if 'text/html' not in url_resp.headers['content-type']:
            continue
        url = url_resp.url
        if url.endswith('.jpg'):
            continue
        if 'vimeo' in url:
            continue
        urls.append(url_resp.url)

    logger.info("Found %d articles", len(urls))
    return urls


def get_top_hacker_news_articles(n=5):
    logger.info("Fetching top Hacker news articles")
    source_url = 'http://news.ycombinator.com/best'
    soup = Soup(requests.get(source_url).content)
    urls = []
    for td in soup('td', attrs={'class': 'title'}):
        anchor = td.find('a')
        if not anchor:
            continue
        urls.append(anchor['href'])
        if len(urls) == n:
            break
    return urls


from config import *

token = readability.xauth(
    CONSUMER_KEY, CONSUMER_SECRET, USERNAME, PASSWORD)
rdd = readability.oauth(
    CONSUMER_KEY, CONSUMER_SECRET, token=token)

user = rdd.get_me()

logger.info("Updating readability library")

logger.info("Fetching library")
library_urls = [u.article.url for u in user.bookmarks()]
logger.info("Found %d articles in library", len(library_urls))

# Fetch URLs
urls = get_article_urls_from_twitter_favourites(TWITTER_USERNAME)
urls += get_top_hacker_news_articles()

num_dupes = num_new = num_errors = 0
for url in urls:
    if url in library_urls:
        num_dupes += 1
    else:
        try:
            rdd.add_bookmark(url)
        except ResponseError:
            num_errors += 1
        except Exception, e:
            logger.error("Unexpected exception: %s", e)
            num_errors += 1
        else:
            logger.info("Adding %s", url)
            num_new += 1

logger.info("Added %d new articles, found %d dupes, %d errors",
            num_new, num_dupes, num_errors)
