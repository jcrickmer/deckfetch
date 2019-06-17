# -*- coding: utf-8 -*-
from dateutil.parser import parse as dtparse
import scrapy
from deckfetch.items import DeckItem
from deckfetch.items import TournamentItem
from scrapy.spiders import CrawlSpider, Rule, Request
import re

import logging

from scrapy.utils.project import get_project_settings
settings = get_project_settings()


FORMAT_FIND_RE = re.compile(r'A (\S+) [Mm]agic deck')
PLACE_FIND_RE = re.compile(r'(\d+)\D{0,2} [Pp]lace')
GET_NUMBER_RE = re.compile(r'^(\d+)')
DECK_ID_RE = re.compile(r'/decks/(\d+)')


class StarCitySpider(CrawlSpider):
    name = "starcity"
    allowed_domains = ["starcitygames.com"]
    download_delay = 21.0 / 8
    start_urls = []
    semaphor_filename = './starcity_last_good_deck_id'
    last_deck_id = 130200
    # MODERN tournaments have a t[T3] value of 28
    # STANDARD tournaments have a t[T1] value of 1

    def __init__(self, *args, **kwargs):
        super(StarCitySpider, self).__init__(*args, **kwargs)
        self.semaphor_filename = settings.get('STARCITY_SEMAPHOR_FILENAME', default='./starcity_last_good_deck_id')
        self.last_deck_id = int(settings.get('STARCITY_START_DECK_ID', default=130200)) + 1
        try:
            scsf = open(self.semaphor_filename, 'r')
            last_id_raw = scsf.read()
            self.last_deck_id = int(str(last_id_raw).strip())
            self.log("Semaphor file \"{}\" reports last_deck_id of {}.".format(
                self.semaphor_filename, self.last_deck_id), level=logging.INFO)
            scsf.close()
        except BaseException as be:
            self.log(
                "Unable to read last deck_id semaphor file. Going with configured default of {}. Stack trace follows.".format(
                    self.last_deck_id),
                level=logging.INFO)
            self.log(be, level=logging.INFO)

        self.start_urls.append('http://www.starcitygames.com/decks/{}'.format(self.last_deck_id + 1))

    def _requests_to_follow(self, response):
        self.log("_requests_to_follow for url {}".format(response.url))
        deck_id = -1
        deck_id_m = DECK_ID_RE.search(response.url)
        if deck_id_m:
            deck_id = int(deck_id_m.group(1))
        # are we at the end of our rope?
        the_end = ' '.join(response.xpath('//span[contains(@class, "titletext")]/text()').extract()).strip().lower()
        self.log("The end is \"{}\"".format(the_end))
        if the_end == 'That Deck Could Not Be Found'.lower():
            # let's think of this as the LAST DECK to try to fetch
            self.log(
                "The URL \"{}\" appears to be the last deck. So we are stopping at deck id {}.".format(
                    response.url, deck_id), level=logging.INFO)
            # However, if the man upstirs says that there is more to do, let's defer to him.
            result = super()._requests_to_follow(response)
            yield
        else:
            scsf = open(self.semaphor_filename, 'w')
            scsf.write('{}\n'.format(deck_id))
            scsf.close()
            next_deck_id = deck_id + 1
            self.log("Adding deck id {} to the queue for fetching and parsing.".format(next_deck_id), level=logging.INFO)
            req = Request(url='http://www.starcitygames.com/decks/{}'.format(next_deck_id))
            yield req

    def parse_start_url(self, response):
        # For now, let's SKIP cached results
        if 'cached' in response.flags:
            # REVISIT - in the future, maybe we pass on cached items? But maybe not... maybe that all belongs at the pipeline level
            pass
        try:
            if True or response.url.index('displaydeck.php'):
                deck = self.parse_deck(response)
                if deck is not None and len(deck) > 0:
                    self.log("Parsed deck from {}, with deck name \"{}\"".format(response.url, deck['name']), level=logging.INFO)
                    yield deck
                    td_o = dtparse(deck['tournament_date'])
                    titem = TournamentItem(name=deck['tournament_name'],
                                           url=deck['tournament_url'],
                                           tournament_format=deck['deck_format'],
                                           start_date=td_o,
                                           end_date=td_o)
                    self.log(
                        "Parsed tournament from {}, with tournament name \"{}\"".format(
                            response.url, titem['name']), level=logging.INFO)
                    yield titem
        except ValueError as ve:
            pass

    def parse_deck(self, response):
        self.log('Parsing deck from {}'.format(response.url), level=logging.INFO)
        # name
        name = ' '.join(response.xpath('//header[contains(@class, "deck_title")]/a/text()').extract())
        self.log('  name: {}'.format(name))

        # author
        author = ' '.join(response.xpath('//header[contains(@class, "player_name")]/a/text()').extract())
        self.log('  author: {}'.format(author))

        # url
        url = response.url

        # place
        place_str = ' '.join(response.xpath('//header[contains(@class, "deck_played_place")]/text()').extract())
        findplace = re.compile(r'^\s*(\d+)')
        fp_m = findplace.search(place_str)
        place = 99999
        if fp_m:
            place = int(fp_m.group(1))
        self.log('  place: {}'.format(str(place)))

        # tournament_url
        tournament_urla = response.xpath('//header[contains(@class, "deck_played_place")]/a/@href').extract()
        if (name is None or len(name) == 0) and (author is None or len(author) == 0) and (
                tournament_urla is None or len(tournament_urla) == 0):
            # let's bail - I bet we don't have a real deck
            self.log('bailing on deck parse - we don\'t have any good signs yet.')
            # close()
            return None
        tournament_url = tournament_urla[0]
        self.log('  tournament_url: {}'.format(tournament_url))

        # deck_format
        deck_format = ''.join(response.xpath('//div[contains(@class, "deck_format")]/text()').extract())
        self.log('  deck_format: {}'.format(deck_format))

        if deck_format is None or len(deck_format) < 3:
            # There is not enough deck here to continue. Bail.
            self.log('Not enough meat to continue trying to parse this deck. Returning None.')
            return None

        # tournament_name
        tournament_name = ' '.join(response.xpath('//header[contains(@class, "deck_played_place")]/a/text()').extract())
        self.log('  tournament_name: {}'.format(tournament_name))

        # tournament_date
        td_str = ' '.join(response.xpath('//header[contains(@class, "deck_played_place")]/text()').extract())
        findtd = re.compile(r'\s+(\d+/\d+/\d+)\s*')
        ftd_m = findtd.search(td_str)
        tournament_date = None
        if ftd_m:
            tournament_date = ftd_m.group(1)
        self.log('  tournament_date: {}'.format(tournament_date))

        # formulated name
        t_name = '{} {} {}'.format(tournament_name, deck_format, tournament_date)
        self.log('  fixed tournament name: {}'.format(t_name))

        mainboard_lines = list()
        sideboard_lines = list()

        # mainboard_cards
        for colsc in range(1, 3):
            for ulc in range(1, 8):
                escape_hatch = 0
                for mbc in range(1, 100):
                    foo = response.xpath(
                        '//div[contains(@class, "cards_col' +
                        str(colsc) + '")]/ul[' + str(ulc) + ']/li[' + str(mbc) + ']/text()').extract()
                    cname = response.xpath(
                        '//div[contains(@class, "cards_col' +
                        str(colsc) + '")]/ul[' + str(ulc) + ']/li[' + str(mbc) + ']/a/text()').extract()
                    if len(cname) != 0:
                        cardcount = 1
                        if len(foo) > 0:
                            cardcount = int(foo[0])
                        the_line = '{} {}'.format(str(cardcount), cname[0].strip())
                        mainboard_lines.append(the_line)
                        self.log('  card: {}'.format(the_line))
                    else:
                        escape_hatch = escape_hatch + 1
                        if escape_hatch > 2:
                            #self.log('out on {}'.format(str(mbc)))
                            break
                        next

        # sideboard_cards
        escape_hatch = 0
        for mbc in range(1, 100):
            foo = response.xpath('//div[contains(@class, "deck_sideboard")]/ul/li[' + str(mbc) + ']/text()').extract()
            cname = response.xpath('//div[contains(@class, "deck_sideboard")]/ul/li[' + str(mbc) + ']/a/text()').extract()
            if len(cname) != 0:
                cardcount = 1
                if len(foo) > 0:
                    cardcount = int(foo[0])
                the_line = '{} {}'.format(str(cardcount), cname[0].strip())
                sideboard_lines.append(the_line)
                self.log('  sb card: {}'.format(the_line))
            else:
                escape_hatch = escape_hatch + 1
                if escape_hatch > 2:
                    #self.log('out on {}'.format(str(mbc)))
                    break
                next

        deck = DeckItem(
            url=url,
            author=author,
            name=name,
            place=place,
            tournament_url=tournament_url,
            deck_format=deck_format,
            tournament_date=tournament_date,
            tournament_name=t_name)
        deck['mainboard_cards'] = mainboard_lines
        deck['sideboard_cards'] = sideboard_lines

        return deck

    def parse_printdeck(self, response):
        #self.log('Found deck at {}'.format(response.url))
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
        #self.log("FORMAT: " + str(formatname))
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
            #self.log("CITY: " + str(cities[0]))
            city = str(cities[0])
        states = response.xpath('//a[contains(@href, "state=")]/text()').extract()
        if len(states) > 0:
            #self.log("STATE: " + str(states[0]))
            pass
        countries = response.xpath('//a[contains(@href, "country=")]/text()').extract()
        if len(countries) > 0:
            #self.log("COUNTRY: " + str(countries[0]))
            pass
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
        #self.log("MAIN: " + str(mainboard_lines))
        #self.log("SIDE: " + str(sideboard_lines))
        deck['mainboard_cards'] = mainboard_lines
        deck['sideboard_cards'] = sideboard_lines
        #self.log("DECK: " + str(deck))
        yield deck

        td_o = dtparse(deck['tournament_date'])
        titem = TournamentItem(name='StarCityGames.com {} in {} {}'.format(deck['deck_format'], city, deck['tournament_date']),
                               url=deck['tournament_url'],
                               tournament_format=deck['deck_format'],
                               tournament_date=td_o)
        yield titem
