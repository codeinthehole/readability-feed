#!/usr/bin/env python

# Config
import logging
import requests
import re
import os
import readability
from readability.api import ResponseError
from BeautifulSoup import BeautifulSoup as Soup
import twitter

from config import *

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


def is_url_an_article(url):
    """
    Test heuristically if the passed URL is an article
    """
    if url.endswith('.jpg'):
        return False
    banned_words = ('vimeo', 'youtube')
    for word in banned_words:
        if word in url:
            return False
    return True


def get_article_urls_from_twitter_favourites(username, n=20):
    """
    Return a list of article URLs extracted from a user's twitter favourites
    """
    logger.info("Fetching articles from Twitter favourite for %s", username)
    api = twitter.Api(
        consumer_key=TWITTER_CONSUMER_KEY,
        consumer_secret=TWITTER_CONSUMER_SECRET,
        access_token_key=TWITTER_ACCESS_TOKEN_KEY,
        access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
    )
    favourites = api.GetFavorites()

    urls = []
    for tweet in favourites:
        text = tweet.text

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
        if is_url_an_article(url):
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


def get_economist_articles(num=10):
    logger.info("Fetching top Economist articles")
    source_url = 'http://www.economist.com'
    soup = Soup(requests.get(source_url).content)
    ul = soup.find('ul', id='recommended-list')
    urls = []
    for anchor in ul.findAll('a'):
        urls.append(source_url + anchor['href'])
    return urls[:num]


def get_atlantic_articles(num=10):
    logger.info("Fetching top Atlantic articles")
    source_url = 'http://www.theatlantic.com'
    soup = Soup(requests.get(source_url).content)
    div = soup.find('div', id='mostPopular')
    urls = []
    for anchor in div.findAll('a'):
        urls.append(source_url + anchor['href'])
    return urls[:num]


def main():
    token = readability.xauth(
        CONSUMER_KEY, CONSUMER_SECRET, USERNAME, PASSWORD)
    rdd = readability.oauth(
        CONSUMER_KEY, CONSUMER_SECRET, token=token)
    user = rdd.get_me()

    logger.info("Updating readability library")

    library_urls = [u.article.url for u in user.bookmarks()]
    logger.info("Found %d articles in library", len(library_urls))

    # Fetch URLs
    urls = get_article_urls_from_twitter_favourites(TWITTER_USERNAME)
    urls += get_top_hacker_news_articles(5)
    urls += get_economist_articles(5)
    urls += get_atlantic_articles(2)  # Only 3 as it's too noisy
    logger.info("Found %d articles to add", len(urls))

    num_dupes = num_new = num_errors = 0
    for url in urls:
        if url in library_urls:
            num_dupes += 1
        else:
            logger.info("Adding %s", url)
            try:
                rdd.add_bookmark(url)
            except ResponseError:
                num_errors += 1
            except Exception, e:
                logger.error("Unexpected exception: %s", e)
                num_errors += 1
            else:
                num_new += 1

    logger.info("Added %d new articles, found %d dupes, %d errors",
                num_new, num_dupes, num_errors)

if __name__ == '__main__':
    main()
