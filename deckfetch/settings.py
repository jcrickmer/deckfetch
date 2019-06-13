# -*- coding: utf-8 -*-

# Scrapy settings for deckfetch project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#

BOT_NAME = 'df'

SPIDER_MODULES = ['deckfetch.spiders']
NEWSPIDER_MODULE = 'deckfetch.spiders'

HTTPCACHE_ENABLED = True
HTTPCACHE_DIR = '/var/deckfetch/cache'
HTTPCACHE_POLICY = 'scrapy.extensions.httpcache.DummyPolicy'
#HTTPCACHE_POLICY = 'scrapy.extensions.httpcache.RFC2616Policy'
HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'

DEPTH_LIMIT = 0

# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'deckfetch (+http://www.yourdomain.com)'

ITEM_PIPELINES = {
    'deckfetch.pipelines.TournamentPipeline': 200,
    'deckfetch.pipelines.DeckPipeline': 300,
}

DOWNLOADER_MIDDLEWARES = {
    # 'deckfetch.middlewares.DedupMiddleware': 0
}

PIPELINE_DECK_DIR = '/var/deckfetch/json/'
PIPELINE_TOURNAMENT_DIR = '/var/deckfetch/json/'
