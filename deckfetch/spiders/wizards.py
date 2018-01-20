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
from daterangeparser import parse as rangeparse
import sys
from deckfetch.unicsv import UnicodeReader
import pyparsing

TAG_RE = re.compile(r'<[^>]+>')


def remove_tags(text):
    return TAG_RE.sub('', text)


class WizardsSpider(CrawlSpider):
    name = "wizards"
    allowed_domains = ["wizards.com"]
    download_delay = 15.0 / 9
    start_urls = (
        #'http://magic.wizards.com/en/articles/archive/event-coverage/dragons-tarkir-top-8-decklists-2015-01-08',
        #'http://magic.wizards.com/en/articles/archive/ptq-top-8-decklists/dragons-tarkir-ptq-santa-clara-2015-02-26',
        #'http://magic.wizards.com/en/events/coverage/gptor15',
        #'http://magic.wizards.com/en/events/coverage/gpsao15',
        #'http://magic.wizards.com/en/events/coverage/gpkra15',
        'http://magic.wizards.com/en/events/coverage',
    )
    rules = (
        # Extract links matching 'category.php' (but not matching 'subsection.php')
        # and follow links from them (since no callback means follow=True by default).
        Rule(LinkExtractor(allow=('deck.*list.*\.txt', ), ), callback='parse_deck'),
        Rule(LinkExtractor(allow=('en/events/coverage/', ), deny=('results', 'standings', 'pairings')), follow=True),
        Rule(LinkExtractor(allow=('/node/', ), deny=('results', 'standings', 'pairings')), follow=True),
    )

    def __init__(self, format_name=None,
                 tournament_date=None,
                 tournament_name='Tournament',
                 start_url='http://magic.wizards.com/en/events/coverage',
                 # 'http://magic.wizards.com/en/articles/archive/ptq-top-8-decklists/dragons-tarkir-ptq-santa-clara-2015-02-26',
                 *args, **kwargs):
        super(WizardsSpider, self).__init__(*args, **kwargs)
        #self.start_urls = [start_url]
        self.format_name = format_name
        self.tournament_date = tournament_date
        #self.tournaments_dict = self.init_tournaments_csv()

    def init_tournaments_csv(self):
        csv_f = open('/tmp/wizards_tournaments.csv', 'rb')
        csv_ur = UnicodeReader(csv_f)
        row = csv_ur.next()  # skip first row, it has headings
        row = csv_ur.next()
        while row is not None:
            for idx in range(0, len(row)):
                for sillydash in [u'\u2010', u'\u2011', u'\u2012', u'\u2013', '\u2014', '\u2015', '\u2212']:
                    if row[idx].find(sillydash) > -1:
                        row[idx] = row[idx].replace(sillydash, u'-')
            fmt = 'Not Supported'
            for supfmt in ['Modern', 'Standard', 'Commander', 'Tiny Leaders']:
                if row[5].find(supfmt) > -1:
                    fmt = supfmt
                    break
            st_date, end_date = rangeparse(row[6])
            row[3] = row[3].replace('*', '').strip()
            tourn = {'event': row[1],
                     'city': row[3],
                     'format': fmt,
                     'start_date': st_date,
                     'end_date': end_date
                     }
            try:
                sys.stderr.write("tourn: {}\n".format(tourn))
            except exceptions.UnicodeEncodeError as uee:
                sys.stderr.write("FOOLISH PYTHON\n")
            row = csv_ur.next()
        return dict()

    def parse_start_url(self, response):
        self.log('yo bro {}'.format(response.url))
        if response.url == 'http://magic.wizards.com/en/events/coverage':
            # go through this document to create valid tournaments
            # for url in response.xpath('//a/@href').extract():
            for bloop in response.xpath('//p').extract():
                try:
                    #self.log('This is a "{}"'.format(str(bloop)))
                    pass
                except exceptions.UnicodeEncodeError:
                    pass
                p_match = re.compile('<p><(strong|b)>([^<]+)</(strong|b)>(.+)</p>$', re.U).match(bloop)
                if p_match:
                    event_type_name = remove_tags(p_match.group(2))
                    stuff = p_match.group(4)
                    lines = stuff.split('<br>')
                    for line in lines:
                        line_re = re.compile(r'href="([^"]+)">(.+)</a> \(([^\)]+)\)([^A-Za-z]+([A-Z].+))?', re.U)
                        line_match = line_re.search(line)
                        if line_match:
                            name = remove_tags(line_match.group(2))
                            fmt = 'Not Supported'
                            try:
                                sys.stderr.write("LINE: '{}'\n".format(line))
                            except exceptions.UnicodeEncodeError:
                                sys.stderr.write("I HATE PYTHON UNICODE SUPPORT\n")

                            if line_match.group(5) is not None:
                                for supfmt in ['Modern', 'Standard', 'Commander', 'Tiny Leaders']:
                                    if line_match.group(5).find(supfmt) > -1:
                                        fmt = supfmt
                                        break
                            if event_type_name == 'Grand Prix':
                                name = u'Grand Prix {}'.format(name)
                            if event_type_name == 'Pro Tour':
                                name = u'Pro Tour {}'.format(name)
                            dates_part = line_match.group(3)
                            if dates_part == 'December 2-3, 7, 2014':
                                dates_part = 'December 2-7, 2014'
                            clean_start_date = None
                            clean_end_date = None
                            try:
                                clean_start_date, clean_end_date = rangeparse(dates_part)
                            except pyparsing.ParseException:
                                pass
                            if clean_start_date is not None and clean_start_date.year > 2010:
                                if clean_end_date is None:
                                    clean_end_date = clean_start_date
                                url = line_match.group(1)
                                if url.find('http') < 0:
                                    url = 'http://magic.wizards.com{}'.format(url)
                                ti = TournamentItem(name=name,
                                                    url=url,
                                                    tournament_format=fmt,
                                                    start_date=clean_start_date,
                                                    end_date=clean_end_date)
                                yield ti

    def parse_deck(self, response):
        self.log('Found deck at {}'.format(response.url))
        deck = DeckItem(url=response.url,
                        tournament_url=response.request.headers['Referer'])

        if self.format_name:
            deck['format_name'] = self.format_name
        # we are going to get the author, deck name, and tournament
        # placement (first, second, third, etc...) from the "n"
        # parameter on the url of this page.
        #
        # example: 'Michael Bonacini\xe2\x80\x99s Mardu Midrange \xe2\x80\x93 2nd'
        url_p = urlparse(response.url)
        qs_d = parse_qs(url_p.query)
        qs_d = self.encoded_dict(qs_d)

        # Some decks have had this crazy name from the URL
        n_re = re.compile('^(.+)\\xe2\\x80\\x99s(.+)(\\xe2\\x80\\x93[^0-9]*([0-9]+))?')  # , re.UNICODE)
        #self.log('Matching "{}"'.format(str(qs_d['n'][0])))
        n_match = n_re.match(str(qs_d['n'][0]))
        if n_match:
            deck['author'] = str(n_match.group(1)).strip()
            deck['name'] = str(n_match.group(2)).strip()
            if n_match.group(4):
                deck['place'] = str(n_match.group(4)).strip()

        # some decks have no name
        if 'name' not in deck:
            deck['author'] = str(qs_d['n'][0])
            deck['name'] = 'Unnamed Deck'

        line_re = re.compile('^[^0-9]*([0-9]+ +[A-Za-z]+.*)$')
        mainboard_lines = list()
        mainboard_done = False
        sideboard_lines = list()
        for line in str(response.body).splitlines(False):
            line = line.strip()
            # Some unicode identifier marks(???) are showing on at the
            # beginning of the file. Let's clear those out, if we find
            # them.
            mmm = line_re.match(line)
            if mmm:
                line = mmm.group(1)

            if len(mainboard_lines) == 0:
                mainboard_lines.append(line)
            else:
                mainboard_done = mainboard_done or line == ''
                if not mainboard_done and len(line) > 0:
                    mainboard_lines.append(line)
                else:
                    if len(line) > 0:
                        sideboard_lines.append(line)
        deck['mainboard_cards'] = mainboard_lines
        deck['sideboard_cards'] = sideboard_lines
        return deck

    def encoded_dict(self, in_dict):
        out_dict = {}
        for k, v in in_dict.iteritems():
            if isinstance(v, unicode):
                v = v.encode('utf8')
            elif isinstance(v, str):
                # Must be encoded in UTF-8
                v.decode('utf8')
            out_dict[k] = v
        return out_dict
