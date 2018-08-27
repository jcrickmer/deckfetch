# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import json
import scrapy
import os
import re


class DeckPipeline(object):

    def __init__(self, *args, **kwargs):
        super(DeckPipeline, self).__init__(*args, **kwargs)
        self.counter = 0

    def process_item(self, item, spider):
        settings = spider.settings
        if 'mainboard_cards' in item and 'name' in item and 'author' in item:
            pp = ''
            try:
                pp = str(item['page_part'])
            except:
                pass
            outfile_name = str(settings.get('PIPELINE_DECK_DIR', default='./')) + 'deck_{}.json'.format(hash(item['url'] + pp))
            # REVISIT - for now, let's only write files that we have not written in the past
            if not os.path.isfile(outfile_name):
                outfile = open(outfile_name, 'wb')
                line = json.dumps(dict(item)) + "\n"
                #self.log('** Writing "{}" out to "{}".'.format(item['name'], 'deck_{}.json'.format(hash(item['url'])), 'wb'))
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
        if 'name' in item and 'start_date' in item and 'mainboard_cards' not in item:
            if 'url' in item:

                # Wizards has some of their URLs as node ids. Let's get the real customer-facing URL, if we can.
                if item['url'] is not None and item['url'].find('/node') >= 0:
                    reloc = item['url']
                    if reloc.find('http') < 0:
                        reloc = u'http://magic.wizards.com{}'.format(reloc)
                    curlp = os.popen(u'curl -s -I \'{}\' | grep Location: | cut -c 10-1000'.format(reloc))
                    foo = f.read()
                    if foo is not None and len(foo) > 0:
                        foo.strip()
                        item['url'] = foo

            item['start_date'] = item['start_date'].strftime("%Y-%m-%d")
            if 'end_date' in item and item['end_date'] is not None:
                item['end_date'] = item['end_date'].strftime("%Y-%m-%d")
            else:
                item['end_date'] = item['start_date']

            # REVISIT - for now, let's only write new files. In the future, we should write to a temp location, then
            # if there is a difference in the files, copy it to the final location.
            outfile_name = str(settings.get('PIPELINE_TOURNAMENT_DIR', default='./')) + 'tournament_{}.json'.format(hash(item['name']))
            if not os.path.isfile(outfile_name):
                outfile = open(outfile_name, 'wb')
                line = json.dumps(dict(item)) + "\n"
                outfile.write(line)
                outfile.close()
        self.counter = self.counter + 1
        return item
