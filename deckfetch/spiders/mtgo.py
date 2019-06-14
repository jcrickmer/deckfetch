# -*- coding: utf-8 -*-

import scrapy
import re
import dateparser
from deckfetch.items import DeckItem
from deckfetch.items import TournamentItem
import datetime


class MTGOSpider(scrapy.Spider):
    p_re = re.compile(r'\s+([januryfebmchpilgstovdJFMASOND]+\s\d+,\s\d+)')

    name = "mtgo"
    download_delay = 17.0 / 4
    allowed_domains = ["wizards.com"]
    start_urls = []

    date_list = [datetime.datetime.today() - datetime.timedelta(days=x) for x in range(0, 14)]

    for curdate in date_list:
        for formatname in ['legacy', 'competitive-legacy',
                           #'pauper', 'competitive-pauper',
                           'modern', 'competitive-modern',
                           'standard', 'competitive-standard',
                           'commander', 'competitive-commander',
                           ]:
            start_urls.append(
                'https://magic.wizards.com/en/articles/archive/mtgo-standings/{}-constructed-league-{:04d}-{:02d}-{:02d}'.format(
                    formatname,
                    curdate.year,
                    curdate.month,
                    curdate.day))
    #start_urls = ['https://magic.wizards.com/en/articles/archive/mtgo-standings/competitive-modern-constructed-league-2017-10-26']

    def parse(self, response):
        # For now, let's SKIP cached results
        # if 'cached' in response.flags:
        #    return
        tournament = None
        decks = self.parse_decks(response)
        if decks is not None and len(decks) > 0:
            tournament = self.parse_tournament(response)
            yield tournament
            for deck in decks:
                deck['tournament_url'] = tournament['url']
                deck['tournament_name'] = tournament['name']
                deck['deck_format'] = tournament['tournament_format']
                deck['tournament_date'] = tournament['start_date']
                if deck['deck_format'] == 'Commander':
                    # Wizard's MTGO lists put the commander in the sideboard list. Let's pull that out...
                    deck['commandzone_cards'] = [line for line in deck['sideboard_cards']]
                    deck['sideboard_cards'] = None
                yield deck

    def parse_tournament(self, response):
        tname = ' '.join(response.xpath('//div[contains(@id, "main-content")]/h1/span/text()').extract())
        if tname is None or len(tname) == 0:
            tname = ' '.join(response.xpath('//div[contains(@id, "main-content")]/h1/text()').extract())
        self.log('tname: {}'.format(tname))

        formatname = ''
        if 'modern' in tname.lower():
            formatname = 'Modern'
        elif 'standard' in tname.lower():
            formatname = 'Standard'
        elif 'commander' in tname.lower():
            formatname = 'Commander'
        elif 'edh' in tname.lower():
            formatname = 'Commander'
        elif 'tiny' in tname.lower():
            formatname = 'TinyLeaders'
        elif 'pauper' in tname.lower():
            formatname = 'Pauper'
        elif 'legacy' in tname.lower():
            formatname = 'Legacy'

        posted = ' '.join(response.xpath('//div[contains(@id, "main-content")]/p[contains(@class, "posted-in")]/text()').extract())
        self.log('posted: {}'.format(posted))

        p_re_m = self.p_re.search(posted)
        tournament_date = None
        if p_re_m:
            tournament_date = dateparser.parse(p_re_m.group(1)).date()
        if not isinstance(tournament_date, str):
            tournament_date = '{:%Y-%m-%d}'.format(tournament_date)
        self.log('tournament_date: {}'.format(tournament_date))

        # formulated name
        t_name = 'MTGO {} {} ({})'.format(tname.strip(), tournament_date.strip(), formatname.strip())
        self.log('fixed tournament name: {}'.format(t_name))

        titem = TournamentItem(name=t_name,
                               url=response.url,
                               tournament_format=formatname,
                               start_date=tournament_date,
                               end_date=tournament_date)
        return titem

    def parse_decks(self, response):
        result = []
        decklists = response.xpath('//div[contains(@class, "decklists")]/div')

        for index, deckblock in enumerate(decklists):
            player_title_l = deckblock.xpath('.//h4/text()').extract()
            player_title = ''
            if player_title_l is not None and isinstance(player_title_l, list) and len(player_title_l) > 0:
                player_title = player_title_l[0]
            self.log('deck: {}'.format(player_title))
            player = ''
            try:
                player = player_title[0:player_title.index(' (')]
            except BaseException:
                player = player_title

            #mainboard_lines = list()
            #sideboard_lines = list()
            blocks = {
                'main': {
                    'lines': list(),
                    'blocks': deckblock.xpath('.//div[contains(@class, "deck-list-text")]/div[contains(@class, "sorted-by-overview-container")]/div/span[contains(@class, "row")]')},
                'side': {
                    'lines': list(),
                    'blocks': deckblock.xpath('.//div[contains(@class, "deck-list-text")]/div[contains(@class, "sorted-by-sideboard-container")]/span[contains(@class, "row")]')}}
            for block_section in blocks:
                block = blocks[block_section]
                for ind2, cardblock in enumerate(block['blocks']):
                    ccount_l = cardblock.xpath('.//span[contains(@class, "card-count")]/text()').extract()

                    # In some cases, Wizard's website will NOT put the name of a card in an a href. So, we need
                    # to handle both cases.
                    cardname_l = cardblock.xpath('.//span[contains(@class, "card-name")]/a/text()').extract()
                    if len(cardname_l) == 0:
                        # there is not "a" element. Let's just get the text.
                        cardname_l = cardblock.xpath('.//span[contains(@class, "card-name")]/text()').extract()
                    #self.log("ccount_l=\"{}\"  ; cardname_l=\"{}\"".format(ccount_l[0], cardname_l[0]))
                    ccount = '1'
                    if ccount_l is not None and len(ccount_l) > 0:
                        ccount = ccount_l[0]
                    if cardname_l is not None and len(cardname_l) > 0:
                        block['lines'].append('{} {}'.format(str(ccount), str(cardname_l[0])))

            deck = DeckItem(url=response.url, author=player, name=player, place=1)
            deck['mainboard_cards'] = blocks['main']['lines']
            deck['sideboard_cards'] = blocks['side']['lines']
            deck['page_part'] = index
            result.append(deck)
        return result
