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
    download_delay = 21.0 / 8
    start_urls = [
        #'http://www.starcitygames.com/pages/decklists/',
        #'http://sales.starcitygames.com/deckdatabase/displaydeck.php?DeckID={}'.format(str(nmbr)) for nmbr in range(81250, 82777)
        #'http://sales.starcitygames.com/deckdatabase/deckshow.php?event_ID=45&t[T3]=28&start_date=2015-04-04&end_date=2015-04-05&order_1=finish&limit=8&action=Show+Decks&city=Syracuse',
        # r'http://sales.starcitygames.com//deckdatabase/deckshow.php?t%5BT1%5D=1&t%5BT3%5D=28&event_ID=&feedin=&start_date=04%2F01%2F2015&end_date=05%2F10%2F2015&city=&state=&country=&start=&finish=&exp=&p_first=&p_last=&simple_card_name%5B1%5D=&simple_card_name%5B2%5D=&simple_card_name%5B3%5D=&simple_card_name%5B4%5D=&simple_card_name%5B5%5D=&w_perc=0&g_perc=0&r_perc=0&b_perc=0&u_perc=0&a_perc=0&comparison%5B1%5D=%3E%3D&card_qty%5B1%5D=1&card_name%5B1%5D=&comparison%5B2%5D=%3E%3D&card_qty%5B2%5D=1&card_name%5B2%5D=&comparison%5B3%5D=%3E%3D&card_qty%5B3%5D=1&card_name%5B3%5D=&comparison%5B4%5D=%3E%3D&card_qty%5B4%5D=1&card_name%5B4%5D=&comparison%5B5%5D=%3E%3D&card_qty%5B5%5D=1&card_name%5B5%5D=&sb_comparison%5B1%5D=%3E%3D&sb_card_qty%5B1%5D=1&sb_card_name%5B1%5D=&sb_comparison%5B2%5D=%3E%3D&sb_card_qty%5B2%5D=1&sb_card_name%5B2%5D=&card_not%5B1%5D=&card_not%5B2%5D=&card_not%5B3%5D=&card_not%5B4%5D=&card_not%5B5%5D=&order_1=finish&order_2=&limit=25&action=Show+Decks&p=1',
        #'http://sales.starcitygames.com/deckdatabase/displaydeck.php?DeckID=84352',
    ]
    #deckids_to_get = range(59000, 62000)
    #deckids_to_get = range(62000, 68000)
    #deckids_to_get = range(73000,84723)
    #deckids_to_get = range(84862, 85045)
    #deckids_to_get = range(85045, 85619)
    #deckids_to_get = range(85619, 88671)
    #deckids_to_get = range(88671, 91300)
    #deckids_to_get = range(98800, 116999)
    #deckids_to_get = range(91300, 112707)
    #deckids_to_get = range(62000, 117677)
    #deckids_to_get = range(117670, 118200)
    deckids_to_get = range(118201, 118259)

    deckids_to_get.reverse()
    for did in deckids_to_get:
        start_urls.append('http://sales.starcitygames.com/deckdatabase/displaydeck.php?DeckID={}'.format(str(did)))

    rules = (
        # Extract links matching 'category.php' (but not matching 'subsection.php')
        # and follow links from them (since no callback means follow=True by default).
        #Rule(LinkExtractor(allow=('displayprintdeck\.php', ), ), callback='parse_printdeck', follow=False),
        # Rule(LinkExtractor(allow=('displaydeck\.php', ), ), callback='parse_deck', follow=False), #follow=True),
        #Rule(LinkExtractor(allow=(r'deckshow\.php'),deny=('start_date=19','start_date=200','start_date=2010','results','standings','pairings','p_first')), follow=True),
    )

    # MODERN tournaments have a t[T3] value of 28
    # STANDARD tournaments have a t[T1] value of 1

    def __init__(self, *args, **kwargs):
        super(StarCitySpider, self).__init__(*args, **kwargs)

    def parse_start_url(self, response):
        try:
            if response.url.index('displaydeck.php'):
                deck = self.parse_deck(response)
                if deck is not None and len(deck) > 0:
                    yield deck
                    self.log('***** DECK IS {}'.format(str(deck)))
                    td_o = dtparse(deck['tournament_date'])
                    titem = TournamentItem(name=deck['tournament_name'],
                                           url=deck['tournament_url'],
                                           tournament_format=deck['deck_format'],
                                           start_date=td_o,
                                           end_date=td_o)
                    yield titem
        except ValueError as ve:
            pass

    def parse_deck(self, response):
        self.log('** PARSING DECK **')
        # name
        name = ' '.join(response.xpath('//header[contains(@class, "deck_title")]/a/text()').extract())
        self.log('name: {}'.format(name))

        # author
        author = ' '.join(response.xpath('//header[contains(@class, "player_name")]/a/text()').extract())
        self.log('author: {}'.format(author))

        # url
        url = response.url
        self.log('url: {}'.format(url))

        # place
        place_str = ' '.join(response.xpath('//header[contains(@class, "deck_played_place")]/text()').extract())
        findplace = re.compile('^\s*(\d+)')
        fp_m = findplace.search(place_str)
        place = 99999
        if fp_m:
            place = int(fp_m.group(1))
        self.log('place: {}'.format(str(place)))

        # tournament_url
        tournament_urla = response.xpath('//header[contains(@class, "deck_played_place")]/a/@href').extract()
        if (name is None or len(name) == 0) and (author is None or len(author) == 0) and (
                tournament_urla is None or len(tournament_urla) == 0):
            # let's bail - I bet we don't have a real deck
            self.log('bailing on deck parse - we don\'t have any good signs yet.')
            # close()
            return None
        tournament_url = tournament_urla[0]
        self.log('tournament_url: {}'.format(tournament_url))

        # deck_format
        deck_format = ''.join(response.xpath('//div[contains(@class, "deck_format")]/text()').extract())
        self.log('deck_format: {}'.format(deck_format))

        if deck_format is None or len(deck_format) < 3:
            # There is not enough deck here to continue. Bail.
            self.log('Not enough meat to continue trying to parse this deck. Returning None.')
            return None

        # tournament_name
        tournament_name = ' '.join(response.xpath('//header[contains(@class, "deck_played_place")]/a/text()').extract())
        self.log('tournament_name: {}'.format(tournament_name))

        # tournament_date
        td_str = ' '.join(response.xpath('//header[contains(@class, "deck_played_place")]/text()').extract())
        findtd = re.compile('\s+(\d+/\d+/\d+)\s*')
        ftd_m = findtd.search(td_str)
        tournament_date = None
        if ftd_m:
            tournament_date = ftd_m.group(1)
        self.log('tournament_date: {}'.format(tournament_date))

        # formulated name
        t_name = '{} {} {}'.format(tournament_name, deck_format, tournament_date)
        self.log('fixed tournament name: {}'.format(t_name))

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
                        self.log('card: {}'.format(the_line))
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
                self.log('sb card: {}'.format(the_line))
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
