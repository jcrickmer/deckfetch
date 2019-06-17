# -*- coding: utf-8 -*-

from deckfetch.items import DeckItem
from deckfetch.items import TournamentItem
import datetime
from calmjs.parse import es5
from calmjs.parse.asttypes import ExprStatement
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor

import json


class DeckStatsSpider(CrawlSpider):

    name = "deckstats"
    download_delay = 17.0 / 4
    allowed_domains = ["deckstats.net"]

    rules = (
        # Extract links matching 'category.php' (but not matching 'subsection.php')
        # and follow links from them (since no callback means follow=True by default).
        Rule(LinkExtractor(allow=(r'decks/[0-9]+/.*/en',), unique=True), callback='parse_deck_page'),
    )

    def __init__(self, *args, **kwargs):
        super(DeckStatsSpider, self).__init__(*args, **kwargs)
        # We are handling the start_urls in the init method because we want to add the current date to the URL to
        # stop from using cached results.
        dfd = '{:%Y%m%d}'.format(datetime.date.today())
        search_age_max = 7
        for page_num in range(1, 4):
            self.start_urls.append(
                'https://deckstats.net/decks/search/?search_order=views%2Cdesc&search_format=10&search_age_max_days={}&lng=en&page={}&dfd={}'.format(
                    search_age_max, page_num, dfd))

    tournament_item = None
    place_count = 1

    def parse_start_url(self, response):
        # overriding the CrawlSpider method to be able to create a TournamentItem first...
        self.log("Parsing for a Tournament now...")
        tournament = self.parse_tournament(response)
        self.tournament_item = tournament
        return self.tournament_item

    def parse_deck_page(self, response):
        tournament = None
        decks = self.parse_decks(response)
        if decks is not None and len(decks) > 0:
            for deck in decks:
                deck['tournament_url'] = self.tournament_item['url']
                deck['tournament_name'] = self.tournament_item['name']
                deck['tournament_date'] = self.tournament_item['start_date']
                yield deck

    def parse_tournament(self, response):
        # For Deckstats.net, since these are not actual tournaments, we are going to treat this list of decks as the
        # ones that are best on this particular day of querying.
        tournament_date = '{:%Y-%m-%d}'.format(datetime.date.today())
        tname = 'DeckStats Commander Top Views {}'.format(tournament_date)
        self.log('Tournament name: {}'.format(tname))
        formatname = 'Commander'
        self.log('Tournament date: {}'.format(tournament_date))

        turl = str(response.url)
        # REVISIT - this is a HACK to get by quickly. A regex would be a much better way to handle this...
        turl = turl.replace('&page=1', '')
        turl = turl.replace('&page=2', '')
        turl = turl.replace('&page=3', '')
        turl = turl.replace('&page=4', '')
        turl = turl.replace('&page=5', '')
        turl = turl.replace('&page=6', '')
        turl = turl.replace('&page=7', '')
        turl = turl.replace('&page=8', '')
        turl = turl.replace('&page=9', '')
        titem = TournamentItem(name=tname,
                               url=turl,
                               tournament_format=formatname,
                               start_date=tournament_date,
                               end_date=tournament_date)
        return titem

    def parse_decks(self, response):
        # 'https://deckstats.net/decks/18708/108521-big-slash-huge/en'
        result = []
        legal = ''
        try:
            # format....
            legal = response.xpath('.//div[contains(@id, "deck_overview_legality")]/text()').extract()
            legal = ''.join(legal)
            legal = legal.strip()
            if legal.startswith('Legal in '):
                legal = legal[len('Legal in '):]
                if 'edh' in legal.lower() or 'commander' in legal.lower():
                    legal = 'Commander'
        except BaseException as be:
            self.log(be)

        scripts = response.xpath('//script')

        deckstats_deck_obj = {}
        for index, script in enumerate(scripts):
            # This will grab the text of the script element, and then try to parse it using an ECMAScript parser.
            # Once we find the expression that sets deck_json, then we will isolate that and turn it into an object
            # that we can query in Python.
            js_code_list = script.xpath('.//text()').extract()
            js_code = '\n'.join(js_code_list)
            if 'deck_json' in js_code:
                try:
                    program = es5(js_code)
                    for node in program:
                        #self.log("node type is {}".format(type(node)))
                        if isinstance(node, ExprStatement):
                            jsstring = str(node)
                            if jsstring.startswith('deck_json'):
                                # need to trim off the assignment and final semicolon
                                jsstring = jsstring[jsstring.find('{'):len(jsstring) - 1]
                                deckstats_deck_obj = json.loads(jsstring)
                                # REVISIT - we should actually bail here... no need to keep looping.
                                #self.log("node is: {}".format(json.dumps(jsonv)))
                                break
                except ValueError as ve:
                    self.log("parser gave ValueError")
                    self.log(ve)
            if len(deckstats_deck_obj) > 0:
                break
        if deckstats_deck_obj is not None and 'sections' in deckstats_deck_obj:
            deck = DeckItem(url=response.url, author='', name='', place=self.place_count)
            try:
                deck['name'] = deckstats_deck_obj['name']
            except KeyError:
                pass

            raw_name = ''
            raw_name_list = response.xpath('.//div[contains(@id, "deck_folder_subtitle")]/a/text()').extract()
            if len(raw_name_list):
                raw_name = str(raw_name_list[0])
                raw_name = raw_name.strip()
                raw_name = raw_name.replace("'s Decks", '')
                raw_name = raw_name.strip()
            deck['author'] = raw_name
            # deck['deck_format'] = deckstats_deck_obj['name']

            main = list()
            side = list()
            cz = list()
            for section in deckstats_deck_obj['sections']:
                for card in section['cards']:
                    if section['name'] == 'Commander':
                        cz.append('{} {}'.format(card['amount'], card['name']))
                    else:
                        main.append('{} {}'.format(card['amount'], card['name']))
            deck['mainboard_cards'] = main
            deck['sideboard_cards'] = side
            deck['commandzone_cards'] = cz
            deck['page_part'] = 0
            deck['deck_format'] = legal
            if legal == 'Commander':
                # skip deck's that didn't show up as 'Legal in EDH / Commander'. At least for now.
                result.append(deck)
            # REVISIT - Looks liek the list of Links fromth eRules that come back are not guaranteed to be in order.
            # So, this won't be accurate. Just make it all 1 for now.
            #self.place_count += 1

        return result
