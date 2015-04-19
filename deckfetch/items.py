# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy

def jscformatdate(o):
    return o.strftime("%Y-%m-%d")

class DeckItem(scrapy.Item):
    name = scrapy.Field()
    author = scrapy.Field()
    url = scrapy.Field()
    place = scrapy.Field()
    tournament_url = scrapy.Field()
    deck_format = scrapy.Field()
    tournament_date = scrapy.Field()
    mainboard_cards = scrapy.Field()
    sideboard_cards = scrapy.Field()
    
class TournamentItem(scrapy.Item):
    name = scrapy.Field()
    url = scrapy.Field()
    tournament_format = scrapy.Field()
    tournament_date = scrapy.Field(serializer=jscformatdate)
    
