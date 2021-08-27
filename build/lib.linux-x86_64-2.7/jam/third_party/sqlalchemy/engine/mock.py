# engine/mock.py
# Copyright (C) 2005-2020 the SQLAlchemy authors and contributors
# <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

from operator import attrgetter

from . import base
from . import url as _url
from .. import util
from ..sql import ddl
from ..sql import schema


class MockConnection(base.Connectable):
    def __init__(self, dialect, execute):
        self._dialect = dialect
        self.execute = execute

    engine = property(lambda s: s)
    dialect = property(attrgetter("_dialect"))
    name = property(lambda s: s._dialect.name)

    schema_for_object = schema._schema_getter(None)

    def connect(self, **kwargs):
        return self

    def execution_options(self, **kw):
        return self

    def compiler(self, statement, parameters, **kwargs):
        return self._dialect.compiler(
            statement, parameters, engine=self, **kwargs
        )

    def create(self, entity, **kwargs):
        kwargs["checkfirst"] = False

        ddl.SchemaGenerator(self.dialect, self, **kwargs).traverse_single(
            entity
        )

    def drop(self, entity, **kwargs):
        kwargs["checkfirst"] = False

        ddl.SchemaDropper(self.dialect, self, **kwargs).traverse_single(entity)

    def _run_ddl_visitor(
        self, visitorcallable, element, connection=None, **kwargs
    ):
        kwargs["checkfirst"] = False
        visitorcallable(self.dialect, self, **kwargs).traverse_single(element)

    def execute(self, object_, *multiparams, **params):
        raise NotImplementedError()


def create_mock_engine(url, executor, **kw):
    """Create a "mock" engine used for echoing DDL.

    This is a utility function used for debugging or storing the output of DDL
    sequences as generated by :meth:`.MetaData.create_all` and related methods.

    The function accepts a URL which is used only to determine the kind of
    dialect to be used, as well as an "executor" callable function which
    will receive a SQL expression object and parameters, which can then be
    echoed or otherwise printed.   The executor's return value is not handled,
    nor does the engine allow regular string statements to be invoked, and
    is therefore only useful for DDL that is sent to the database without
    receiving any results.

    E.g.::

        from sqlalchemy import create_mock_engine

        def dump(sql, *multiparams, **params):
            print(sql.compile(dialect=engine.dialect))

        engine = create_mock_engine('postgresql://', dump)
        metadata.create_all(engine, checkfirst=False)

    :param url: A string URL which typically needs to contain only the
     database backend name.

    :param executor: a callable which receives the arguments ``sql``,
     ``*multiparams`` and ``**params``.  The ``sql`` parameter is typically
     an instance of :class:`.DDLElement`, which can then be compiled into a
     string using :meth:`.DDLElement.compile`.

    .. versionadded:: 1.4 - the :func:`.create_mock_engine` function replaces
       the previous "mock" engine strategy used with :func:`.create_engine`.

    .. seealso::

        :ref:`faq_ddl_as_string`

    """

    # create url.URL object
    u = _url.make_url(url)

    dialect_cls = u.get_dialect()

    dialect_args = {}
    # consume dialect arguments from kwargs
    for k in util.get_cls_kwargs(dialect_cls):
        if k in kw:
            dialect_args[k] = kw.pop(k)

    # create dialect
    dialect = dialect_cls(**dialect_args)

    return MockConnection(dialect, executor)
