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
import dateparser
import sys
from deckfetch.unicsv import UnicodeReader
import pyparsing

wizards_reference_javascript = '''
For reference, here is the JavaScript code that Wizard's site uses to make a deck list from the content on the page:

function wiz_bean_content_deck_list_generate_file(obj) {
  var breakStr = "[b]";
  var output = "";
  var decklist = obj.parentNode.parentNode;
  var vCard = decklist.querySelectorAll(".sorted-by-overview-container .row");
  var vSideboard = decklist.querySelectorAll(" .sorted-by-sideboard-container .row");
  for(var i = 0; i < vCard.length; i++)
  {
    var count = vCard[i].querySelector(".card-count").innerHTML;
    var name = vCard[i].querySelector(".card-name a").innerHTML;
    output += count + " " + name + breakStr;
  }
  output += breakStr + breakStr;
  for(var i = 0; i < vSideboard.length; i++)
  {
    var count = vSideboard[i].querySelector(".card-count").innerHTML;
    var name = vSideboard[i].querySelector(".card-name a").innerHTML;
    output += count + " " + name + breakStr;
  }
  var title = decklist.querySelector(".deck-meta h4").innerHTML;
     
  $form = jQuery(obj).prev("form");
  jQuery("input[name='title']",$form).val(encodeURIComponent(title));
  jQuery("input[name='content']",$form).val(encodeURIComponent(output));
  jQuery($form).submit();
}


When this is used, "obj" is the "<a href>" that is being clicked. Tis script is being invoked from the onclick event
handler of an a href on a page like
https://magic.wizards.com/en/articles/archive/event-coverage/pro-tour-dragons-maze-qualifier-season-top-8-modern-decklists-201-60
'''


TAG_RE = re.compile(r'<[^>]+>')
DATE_RE = re.compile('\s+([januaryfebmchpilnjulyaugustseptemberoctobernovemberdecemberJFMASOND]+\s\d+,\s\d+)')

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
            for supfmt in ['Modern', 'Standard', 'Commander', 'Legacy', 'Tiny Leaders']:
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
        #self.log('Response for URL "{}", which has flags "{}"'.format(response.url, response.flags))
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
        else:
            # looking for decks on pages like https://magic.wizards.com/en/events/coverage/2018natus/top-8-decklists-2018-07-01
            self.log("Let's try this...")
            if len(response.selector.xpath('//div[@class="deck-group"]')) > 0:
                # this page has deck listings on it!

                ti = TournamentItem()
                # let's get the event name and URL, if we can.
                breadcrumb_tournament = response.selector.xpath('//div[@id="breadcrumb"]/span[not(@class="current")][last()]/a')
                if len(breadcrumb_tournament) > 0:
                    self.log("breadcrumb_tournament = {}".format(breadcrumb_tournament))
                    self.log("breadcrumb_tournament len = {}".format(len(breadcrumb_tournament)))
                    ti['name'] = breadcrumb_tournament.xpath('.//text()').extract()[0]
                    ti['url'] = breadcrumb_tournament.xpath('.//@href').extract()[0]

                # and now try to figure out the date
                posted_in = response.selector.xpath('//p[@class="posted-in"]/text()').extract()
                for val in posted_in:
                    dre_match = DATE_RE.search(val)
                    if dre_match:
                        tdate = dateparser.parse(dre_match.group(1)).date()
                        self.log("date is = {}".format(tdate))
                        ti['start_date'] = tdate
                        ti['end_date'] = tdate
                        break

                # and now the format...
                format_sels = response.selector.xpath('//div[@id="content-detail-page-of-an-article"]/p/text()')
                ti['tournament_format'] = None
                for format_sel in format_sels:
                    if ti['tournament_format'] is None:
                        val = format_sel.extract()
                        if 'Legacy' in val:
                            ti['tournament_format'] = 'Legacy'
                        if 'Standard' in val:
                            ti['tournament_format'] = 'Standard'
                        if 'Modern' in val:
                            ti['tournament_format'] = 'Modern'

                self.log("TournamentItem is {}".format(ti))

                # BOOKMARK - so, if I think I have a valid TournamentItem, I need to yield it
                page_place = 1
                for deckgroup_selector in response.selector.xpath('//div[@class="deck-group"]'):
                    self.parse_deckgroup(response, deckgroup_selector, page_place)
                    page_place += 1

    ##
    ## This is for parsing pages like https://magic.wizards.com/en/events/coverage/2018natus/top-8-decklists-2018-07-01
    ##
    def parse_deckgroup(self, response, deckgroup_selector, page_position):
        self.log("found a div class deck-group")
        self.log("  url: {}".format(response.url))
        self.log("  page_place: {}".format(page_position))
        self.log("  deckgroup_selector is a {}".format(type(deckgroup_selector)))
        title = deckgroup_selector.xpath('.//h4/text()').extract()[0]
        try:
            self.log("  title is: {}".format(title))
        except exceptions.UnicodeEncodeError:
            self.log("  title STUPID PYTHON2 UNICODE")
        deck = DeckItem(url='{}#deck{}'.format(response.url, page_position),
                        tournament_url=response.url)
        deck['mainboard_cards'] = list()
        deck['sideboard_cards'] = list()
        overview_container_rows = deckgroup_selector.xpath('''.//div[contains(concat(' ',normalize-space(@class),' '),' sorted-by-overview-container ')]//*[@class="row"]''')
        for item in overview_container_rows:
            # this has a couple of spans with classes card-count and card-name. the card-name span has an A element.
            #self.log("  found a overview_container: {}".format(item))
            card_count = item.xpath('.//*[@class="card-count"]/text()').extract()[0]
            #self.log("    card count is {}".format(card_count))
            card_name = item.xpath('.//*[@class="card-name"]/a/text()').extract()[0]
            #self.log("    card name is {}".format(card_name))
            # BOOKMARK!!! we have a deck with mainboard cards!!
            deck['mainboard_cards'].append('{} {}'.format(card_count, card_name))
        sideboard_container_rows = deckgroup_selector.xpath('''.//div[contains(concat(' ',normalize-space(@class),' '),' sorted-by-sideboard-container ')]//*[@class="row"]''')
        for item in sideboard_container_rows:
            # this has a couple of spans with classes card-count and card-name. the card-name span has an A element.
            #self.log("  found a overview_container: {}".format(item))
            card_count = item.xpath('.//*[@class="card-count"]/text()').extract()[0]
            #self.log("    card count is {}".format(card_count))
            card_name = item.xpath('.//*[@class="card-name"]/a/text()').extract()[0]
            #self.log("    card name is {}".format(card_name))
            # BOOKMARK!!! we have a deck with mainboard cards!!
            deck['sideboard_cards'].append('{} {}'.format(card_count, card_name))
        self.log("DeckItem is {}".format(deck))

        # BOOKMARK - if I think I have a valid DeckItem, I need to yield it.

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
