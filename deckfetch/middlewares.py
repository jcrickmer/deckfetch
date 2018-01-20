# -*- coding: utf-8 -*-
from scrapy import log
from scrapy.exceptions import IgnoreRequest
import MySQLdb as mdb


class DedupMiddleware(object):

    def __init__(self):
        self.db_cur = None
        try:
            con = mdb.connect('localhost', 'root', 'godzilla', 'mtgdb')
            self.db_cur = con.cursor()
        except mdb.Error as e:
            log.msg("Error connecting to database - %d: %s" % (e.args[0], e.args[1]), level=log.ERROR)

    def process_request(self, request, spider):
        if self.db_cur is not None:
            db_res = self.db_cur.execute('SELECT id FROM deck WHERE url = %s', [request.url])
            if self.db_cur.fetchone():
                log.msg('Ignore url that has already been fetched: <%s>' % url, level=log.DEBUG)
                raise IgnoreRequest()
