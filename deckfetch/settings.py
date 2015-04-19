# -*- coding: utf-8 -*-

# Scrapy settings for deckfetch project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#

BOT_NAME = 'deckfetch'

SPIDER_MODULES = ['deckfetch.spiders']
NEWSPIDER_MODULE = 'deckfetch.spiders'

HTTPCACHE_ENABLED = True
HTTPCACHE_DIR = '/tmp/deckfetch_cache'
HTTPCACHE_POLICY = 'scrapy.contrib.httpcache.DummyPolicy'
HTTPCACHE_STORAGE = 'scrapy.contrib.httpcache.FilesystemCacheStorage'

DEPTH_LIMIT = 2

# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'deckfetch (+http://www.yourdomain.com)'

ITEM_PIPELINES = {
    'deckfetch.pipelines.TournamentPipeline': 200,
    'deckfetch.pipelines.DeckPipeline': 300,
}
 
