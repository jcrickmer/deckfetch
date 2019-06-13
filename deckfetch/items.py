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
    tournament_name = scrapy.Field()
    deck_format = scrapy.Field()
    tournament_date = scrapy.Field()
    mainboard_cards = scrapy.Field()
    sideboard_cards = scrapy.Field()
    commandzone_cards = scrapy.Field()
    page_part = scrapy.Field()


class TournamentItem(scrapy.Item):
    name = scrapy.Field()
    url = scrapy.Field()
    tournament_format = scrapy.Field()
    start_date = scrapy.Field(serializer=jscformatdate)
    end_date = scrapy.Field(serializer=jscformatdate)
