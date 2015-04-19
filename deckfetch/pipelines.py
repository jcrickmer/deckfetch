# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import json
import scrapy


class DeckPipeline(object):

    def __init__(self, *args, **kwargs):
        super(DeckPipeline, self).__init__(*args, **kwargs)
        self.counter = 0

    def process_item(self, item, spider):
        settings = spider.settings
        if 'mainboard_cards' in item and 'name' in item and 'author' in item:
            outfile = open(str(settings.get('PIPELINE_DECK_DIR', default='./')) + 'deck_{}.json'.format(hash(item['url'])), 'wb')
            line = json.dumps(dict(item)) + "\n"
            outfile.write(line)
            outfile.close()
        self.counter = self.counter + 1
        return item


class TournamentPipeline(object):

    def __init__(self, *args, **kwargs):
        super(TournamentPipeline, self).__init__(*args, **kwargs)
        self.counter = 0

    def process_item(self, item, spider):
        settings = spider.settings
        if 'name' in item and 'tournament_date' in item and 'mainboard_cards' not in item:
            item['tournament_date'] = item['tournament_date'].strftime("%Y-%m-%d")
            outfile = open(str(settings.get('PIPELINE_TOURNAMENT_DIR', default='./')) +
                           'tournament_{}.json'.format(hash(item['url'])), 'wb')
            line = json.dumps(dict(item)) + "\n"
            outfile.write(line)
            outfile.close()
        self.counter = self.counter + 1
        return item
