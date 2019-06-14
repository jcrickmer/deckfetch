# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import json
import os

import datetime
import base64
import hashlib

import logging
logger = logging.getLogger(__name__)


def hash_val(val):
    h = base64.b16encode(hashlib.md5(val.encode('utf-8')).digest())
    return str(h[:16], encoding='utf-8')


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
            except BaseException:
                pass
            url_pp_hash = hash_val('{}{}'.format(item['url'], pp))
            logger.debug("Writing deck out to file with hash \"{}\"\n".format(url_pp_hash))
            outfile_name = settings.get('PIPELINE_DECK_DIR', default='./') + 'deck_{}.json'.format(url_pp_hash)
            # REVISIT - for now, let's only write files that we have not written in the past. The reason for doing
            # this is so that we do not make the loaddecks management command accedentally load the same deck twice
            # because the file stamp is newer. This is not a good policy and needs to be fixed.
            if True or not os.path.isfile(outfile_name):
                try:
                    outfile = open(outfile_name, 'w', encoding='utf-8')
                    if isinstance(item['tournament_date'], datetime.date):
                        # need to smartly force the date to a normal string reprsentation of the date
                        item['tournament_date'] = '{:%Y-%m-%d}'.format(item['tournament_date'])
                    else:
                        # force to a string anyway
                        item['tournament_date'] = '{}'.format(item['tournament_date'])
                    line = json.dumps(dict(item)) + "\n"
                    #logger.info('** Writing "{}" out to "{}".'.format(item['name'], 'deck_{}.json'.format(hash(item['url'])), 'wb'))
                    outfile.write(line)
                    outfile.close()
                except BaseException as be:
                    logger.error("Unable to write deck pipeline for URL '{}' out to '{}'".format(item['url'], outfile_name))
                    logger.error(be, exc_info=True)
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
                        reloc = 'http://magic.wizards.com{}'.format(reloc)
                    curlp = os.popen('curl -s -I \'{}\' | grep Location: | cut -c 10-1000'.format(reloc))
                    foo = f.read()
                    if foo is not None and len(foo) > 0:
                        foo.strip()
                        item['url'] = foo

            if isinstance(item['start_date'], datetime.datetime):
                item['start_date'] = item['start_date'].strftime("%Y-%m-%d")

            if 'end_date' in item and item['end_date'] is not None and isinstance(item['end_date'], datetime.datetime):
                item['end_date'] = item['end_date'].strftime("%Y-%m-%d")
            else:
                item['end_date'] = item['start_date']

            # REVISIT - for now, let's only write new files. In the future, we should write to a temp location, then
            # if there is a difference in the files, copy it to the final location.
            t_hash = hash_val(item['name'])
            logger.debug("Writing tournament out to file with hash \"{}\"\n".format(t_hash))
            outfile_name = settings.get('PIPELINE_TOURNAMENT_DIR', default='./') + 'tournament_{}.json'.format(t_hash)
            if True or not os.path.isfile(outfile_name):
                outfile = open(outfile_name, 'w', encoding="utf8")
                line = json.dumps(dict(item)) + "\n"
                outfile.write(line)
                outfile.close()
        self.counter = self.counter + 1
        return item
