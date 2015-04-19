# -*- coding: utf-8 -*-
import scrapy
from deckfetch.items import DeckItem
from deckfetch.items import TournamentItem
from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors import LinkExtractor
from urlparse import urlparse, parse_qs
import re
import exceptions
from dateutil.parser import parse as dtparse

TAG_RE = re.compile(r'<[^>]+>')


def remove_tags(text):
    return TAG_RE.sub('', text)

FORMAT_FIND_RE = re.compile('A (\S+) [Mm]agic deck')
PLACE_FIND_RE = re.compile('(\d+)\D{0,2} [Pp]lace')
GET_NUMBER_RE = re.compile('^(\d+)')


class StarCitySpider(CrawlSpider):
    name = "starcity"
    allowed_domains = ["starcitygames.com"]
    download_delay = 9.8
    start_urls = [
        #'http://www.starcitygames.com/pages/decklists/',
        'http://sales.starcitygames.com/deckdatabase/displaydeck.php?DeckID={}'.format(str(nmbr)) for nmbr in range(81250, 82777)
        #'http://sales.starcitygames.com/deckdatabase/deckshow.php?event_ID=45&t[T3]=28&start_date=2015-04-04&end_date=2015-04-05&order_1=finish&limit=8&action=Show+Decks&city=Syracuse',
        #'http://sales.starcitygames.com/deckdatabase/deckshow.php?event_ID=45&t[T3]=28&start_date=2015-03-27&end_date=2015-03-29&order_1=finish&limit=8&action=Show+Decks&city=Richmond',
        #'http://sales.starcitygames.com/deckdatabase/deckshow.php?event_ID=45&t[T3]=28&start_date=2015-03-14&end_date=2015-03-15&order_1=finish&limit=8&action=Show+Decks&city=Dallas',
        #'http://sales.starcitygames.com/deckdatabase/deckshow.php?event_ID=47&start_date=2015-02-28&end_date=2015-03-01&order_1=finish&limit=8&action=Show+Decks&city=Baltimore',
    ]

    rules = (
        # Extract links matching 'category.php' (but not matching 'subsection.php')
        # and follow links from them (since no callback means follow=True by default).
        Rule(LinkExtractor(allow=('displayprintdeck\.php', ), ), callback='parse_deck', follow=False),
        #Rule(LinkExtractor(allow=(r'deckshow\.php', r'displaydeck\.php'),deny=('start_date=19','start_date=200','start_date=2010','results','standings','pairings')), follow=True),
    )

    # MODERN tournaments have a t[T3] value of 28
    # STANDARD tournaments have a t[T1] value of 1

    def parse_deck(self, response):
        self.log('Found deck at {}'.format(response.url))
        deck = DeckItem(url=response.url)
        title_l = response.xpath('//span[contains(@class, "titletext")]/a/text()').extract()
        title = title_l[0]
        #self.log("TITLE: " + str(title))
        deck['name'] = str(title)

        formatname = None
        place = 99999
        body_poop = response.xpath('//body/text()').extract()
        for poop in body_poop:
            find_format = FORMAT_FIND_RE.search(poop)
            if find_format:
                formatname = find_format.group(1)
            place_format = PLACE_FIND_RE.search(poop)
            if place_format:
                place = place_format.group(1)
        self.log("FORMAT: " + str(formatname))
        deck['deck_format'] = str(formatname)

        #self.log("PLACE: " + str(place))
        deck['place'] = str(place)

        authornames = response.xpath('//a[contains(@href, "p_first=")]/text()').extract()
        if len(authornames) > 0:
            #self.log("AUTHORNAME: " + str(authornames[0]))
            deck['author'] = str(authornames[0])
        cities = response.xpath('//a[contains(@href, "city=")]/text()').extract()
        city = ''
        if len(cities) > 0:
            self.log("CITY: " + str(cities[0]))
            city = str(cities[0])
        states = response.xpath('//a[contains(@href, "state=")]/text()').extract()
        if len(states) > 0:
            self.log("STATE: " + str(states[0]))
        countries = response.xpath('//a[contains(@href, "country=")]/text()').extract()
        if len(countries) > 0:
            self.log("COUNTRY: " + str(countries[0]))
        start_dates = response.xpath('//a[contains(@href, "start_date=")]/@href').extract()
        if len(start_dates) > 0:
            sd_idx = start_dates[0].find('start_date=')
            if sd_idx > -1:
                start_date = start_dates[0][sd_idx + len('start_date='):sd_idx + len('start_date=') + len('xxxx-yy-zz')]
                #self.log("DATE: " + start_date)
                deck['tournament_date'] = start_date
        end_dates = response.xpath('//a[contains(@href, "end_date=")]/@href').extract()
        end_date = None
        if len(end_dates) > 0:
            sd_idx = end_dates[0].find('end_date=')
            if sd_idx > -1:
                end_date = end_dates[0][sd_idx + len('end_date='):sd_idx + len('end_date=') + len('xxxx-yy-zz')]
        url_base = 'http://sales.starcitygames.com/deckdatabase/deckshow.php?'
        format_part = ''
        if deck['deck_format'].lower() == 'standard':
            format_part = 't[T1]=1'
        elif deck['deck_format'].lower() == 'modern':
            format_part = 't[T3]=28'
        deck['tournament_url'] = url_base + '&'.join([format_part,
                                                      'city=' + city,
                                                      'start_date=' + deck['tournament_date'],
                                                      'end_date=' + end_date])
        mainboard_lines = list()
        sideboard_lines = list()
        for span in response.xpath('//span'):
            class_attrs = span.xpath('@class').extract()
            if len(class_attrs) > 0 and class_attrs[0] == 'titletext':
                # skip
                continue
            kids = span.xpath('*|text()')
            in_sb = False
            cur_num = None
            for kid in kids:
                in_sb = in_sb or kid.extract().find('<strong>Sideboard') > -1
                is_text_number_match = GET_NUMBER_RE.search(str(kid.extract()))
                if is_text_number_match:
                    cur_num = is_text_number_match.group(1)
                else:
                    ggg = kid.xpath('./text()').extract()
                    booh = None
                    if cur_num:
                        booh = '{} {}'.format(str(cur_num), ggg[0].strip())
                        cur_num = None
                        if in_sb:
                            sideboard_lines.append(booh)
                        else:
                            mainboard_lines.append(booh)
        self.log("MAIN: " + str(mainboard_lines))
        self.log("SIDE: " + str(sideboard_lines))
        deck['mainboard_cards'] = mainboard_lines
        deck['sideboard_cards'] = sideboard_lines
        self.log("DECK: " + str(deck))
        yield deck

        td_o = dtparse(deck['tournament_date'])
        titem = TournamentItem(name='StarCityGames.com {} in {} {}'.format(deck['deck_format'], city, deck['tournament_date']),
                               url=deck['tournament_url'],
                               tournament_format=deck['deck_format'],
                               tournament_date=td_o)
        yield titem
