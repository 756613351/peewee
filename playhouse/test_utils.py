from contextlib import contextmanager
from functools import wraps
import logging

from peewee import create_model_tables
from peewee import drop_model_tables


logger = logging.getLogger('peewee')

class test_database(object):
    def __init__(self, db, models, create_tables=True, drop_tables=True,
                 fail_silently=False):
        self.db = db
        self.models = models
        self.create_tables = create_tables
        self.drop_tables = drop_tables
        self.fail_silently = fail_silently

    def __enter__(self):
        self.orig = []
        for m in self.models:
            self.orig.append(m._meta.database)
            m._meta.database = self.db
        if self.create_tables:
            create_model_tables(self.models, fail_silently=self.fail_silently)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.create_tables and self.drop_tables:
            drop_model_tables(self.models, fail_silently=self.fail_silently)
        for i, m in enumerate(self.models):
            m._meta.database = self.orig[i]


class _QueryLogHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        self.queries = []
        logging.Handler.__init__(self, *args, **kwargs)

    def emit(self, record):
        self.queries.append(record)


class count_queries(object):
    def __init__(self, only_select=False):
        self.only_select = only_select
        self.count = 0

    def get_queries(self):
        return self._handler.queries

    def __enter__(self):
        self._handler = _QueryLogHandler()
        logger.setLevel(logging.DEBUG)
        logger.addHandler(self._handler)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.removeHandler(self._handler)
        if self.only_select:
            self.count = len([q for q in self._handler.queries
                              if q.msg[0].startswith('SELECT ')])
        else:
            self.count = len(self._handler.queries)


def assert_query_count(expected, only_select=False):
    def decorator(fn):
        @wraps(fn)
        def inner(self, *args, **kwargs):
            with count_queries(only_select=only_select) as counter:
                ret = fn(self, *args, **kwargs)

            self.assertEqual(counter.count, expected)
            return ret
        return inner

    return decorator
