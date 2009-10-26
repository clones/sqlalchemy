# coding: utf-8
from sqlalchemy.test.testing import eq_, assert_raises, assert_raises_message
from sqlalchemy.test import  engines
import datetime
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy import exc, schema
from sqlalchemy.dialects.postgresql import base as postgresql
from sqlalchemy.engine.strategies import MockEngineStrategy
from sqlalchemy.test import *
from sqlalchemy.sql import table, column
from sqlalchemy.test.testing import eq_

class SequenceTest(TestBase, AssertsCompiledSQL):
    def test_basic(self):
        seq = Sequence("my_seq_no_schema")
        dialect = postgresql.PGDialect()
        assert dialect.identifier_preparer.format_sequence(seq) == "my_seq_no_schema"

        seq = Sequence("my_seq", schema="some_schema")
        assert dialect.identifier_preparer.format_sequence(seq) == "some_schema.my_seq"

        seq = Sequence("My_Seq", schema="Some_Schema")
        assert dialect.identifier_preparer.format_sequence(seq) == '"Some_Schema"."My_Seq"'

class CompileTest(TestBase, AssertsCompiledSQL):
    __dialect__ = postgresql.dialect()

    def test_update_returning(self):
        dialect = postgresql.dialect()
        table1 = table('mytable',
            column('myid', Integer),
            column('name', String(128)),
            column('description', String(128)),
        )

        u = update(table1, values=dict(name='foo')).returning(table1.c.myid, table1.c.name)
        self.assert_compile(u, "UPDATE mytable SET name=%(name)s RETURNING mytable.myid, mytable.name", dialect=dialect)

        u = update(table1, values=dict(name='foo')).returning(table1)
        self.assert_compile(u, "UPDATE mytable SET name=%(name)s "\
            "RETURNING mytable.myid, mytable.name, mytable.description", dialect=dialect)

        u = update(table1, values=dict(name='foo')).returning(func.length(table1.c.name))
        self.assert_compile(u, "UPDATE mytable SET name=%(name)s RETURNING length(mytable.name) AS length_1", dialect=dialect)

        
    def test_insert_returning(self):
        dialect = postgresql.dialect()
        table1 = table('mytable',
            column('myid', Integer),
            column('name', String(128)),
            column('description', String(128)),
        )

        i = insert(table1, values=dict(name='foo')).returning(table1.c.myid, table1.c.name)
        self.assert_compile(i, "INSERT INTO mytable (name) VALUES (%(name)s) RETURNING mytable.myid, mytable.name", dialect=dialect)

        i = insert(table1, values=dict(name='foo')).returning(table1)
        self.assert_compile(i, "INSERT INTO mytable (name) VALUES (%(name)s) "\
            "RETURNING mytable.myid, mytable.name, mytable.description", dialect=dialect)

        i = insert(table1, values=dict(name='foo')).returning(func.length(table1.c.name))
        self.assert_compile(i, "INSERT INTO mytable (name) VALUES (%(name)s) RETURNING length(mytable.name) AS length_1", dialect=dialect)
    
    @testing.uses_deprecated(r".*argument is deprecated.  Please use statement.returning.*")
    def test_old_returning_names(self):
        dialect = postgresql.dialect()
        table1 = table('mytable',
            column('myid', Integer),
            column('name', String(128)),
            column('description', String(128)),
        )

        u = update(table1, values=dict(name='foo'), postgres_returning=[table1.c.myid, table1.c.name])
        self.assert_compile(u, "UPDATE mytable SET name=%(name)s RETURNING mytable.myid, mytable.name", dialect=dialect)

        u = update(table1, values=dict(name='foo'), postgresql_returning=[table1.c.myid, table1.c.name])
        self.assert_compile(u, "UPDATE mytable SET name=%(name)s RETURNING mytable.myid, mytable.name", dialect=dialect)

        i = insert(table1, values=dict(name='foo'), postgres_returning=[table1.c.myid, table1.c.name])
        self.assert_compile(i, "INSERT INTO mytable (name) VALUES (%(name)s) RETURNING mytable.myid, mytable.name", dialect=dialect)
        
    def test_create_partial_index(self):
        tbl = Table('testtbl', MetaData(), Column('data',Integer))
        idx = Index('test_idx1', tbl.c.data, postgresql_where=and_(tbl.c.data > 5, tbl.c.data < 10))

        self.assert_compile(schema.CreateIndex(idx), 
            "CREATE INDEX test_idx1 ON testtbl (data) WHERE testtbl.data > 5 AND testtbl.data < 10", dialect=postgresql.dialect())

    @testing.uses_deprecated(r".*'postgres_where' argument has been renamed.*")
    def test_old_create_partial_index(self):
        tbl = Table('testtbl', MetaData(), Column('data',Integer))
        idx = Index('test_idx1', tbl.c.data, postgres_where=and_(tbl.c.data > 5, tbl.c.data < 10))

        self.assert_compile(schema.CreateIndex(idx), 
            "CREATE INDEX test_idx1 ON testtbl (data) WHERE testtbl.data > 5 AND testtbl.data < 10", dialect=postgresql.dialect())

    def test_extract(self):
        t = table('t', column('col1'))

        for field in 'year', 'month', 'day':
            self.assert_compile(
                select([extract(field, t.c.col1)]),
                "SELECT EXTRACT(%s FROM t.col1::timestamp) AS anon_1 "
                "FROM t" % field)

class EnumTest(TestBase, AssertsExecutionResults, AssertsCompiledSQL):
    __only_on__ = 'postgresql'
    __dialect__ = postgresql.dialect()
    
    def test_compile(self):
        e1 = Enum('x', 'y', 'z', name="somename")
        e2 = Enum('x', 'y', 'z', name="somename", schema='someschema')
        
        self.assert_compile(
            postgresql.CreateEnumType(e1), 
            "CREATE TYPE somename AS ENUM ('x','y','z')"
        )

        self.assert_compile(
            postgresql.CreateEnumType(e2), 
            "CREATE TYPE someschema.somename AS ENUM ('x','y','z')"
        )

        self.assert_compile(
            postgresql.DropEnumType(e1), 
            "DROP TYPE somename"
        )

        self.assert_compile(
            postgresql.DropEnumType(e2), 
            "DROP TYPE someschema.somename"
        )
        
        t1 = Table('sometable', MetaData(), Column('somecolumn', e1))
        self.assert_compile(
            schema.CreateTable(t1),
            "CREATE TABLE sometable ("
            "somecolumn somename"
            ")"
        )
        t1 = Table('sometable', MetaData(), 
                    Column('somecolumn', Enum('x', 'y', 'z', native_enum=False))
                )
        self.assert_compile(
            schema.CreateTable(t1),
            "CREATE TABLE sometable ("
            "somecolumn VARCHAR(1), "
            " CHECK (somecolumn IN ('x','y','z'))"
            ")"
        )

    
    @testing.fails_on('postgresql+zxjdbc', 
                        'zxjdbc fails on ENUM: column "XXX" is of type XXX '
                        'but expression is of type character varying')
    @testing.fails_on('postgresql+pg8000', 
                        'zxjdbc fails on ENUM: column "XXX" is of type XXX '
                        'but expression is of type text')
    def test_create_table(self):
        metadata = MetaData(testing.db)
        t1 = Table('table', metadata,
            Column('id', Integer, primary_key=True),
            Column('value', Enum('one', 'two', 'three', name='onetwothreetype'))
        )
        t1.create()
        t1.create(checkfirst=True) # check the create
        try:
            t1.insert().execute(value='two')
            t1.insert().execute(value='three')
            t1.insert().execute(value='three')
            eq_(t1.select().order_by(t1.c.id).execute().fetchall(), 
                [(1, 'two'), (2, 'three'), (3, 'three')]
            )
        finally:
            metadata.drop_all()
            metadata.drop_all()
    
    def test_name_required(self):
        metadata = MetaData(testing.db)
        etype = Enum('four', 'five', 'six', metadata=metadata)
        assert_raises(exc.ArgumentError, etype.create)
        assert_raises(exc.ArgumentError, etype.compile, dialect=postgresql.dialect())
    
    @testing.fails_on('postgresql+zxjdbc', 
                        'zxjdbc fails on ENUM: column "XXX" is of type XXX '
                        'but expression is of type character varying')
    @testing.fails_on('postgresql+pg8000', 
                        'zxjdbc fails on ENUM: column "XXX" is of type XXX '
                        'but expression is of type text')
    def test_unicode_labels(self):
        metadata = MetaData(testing.db)
        t1 = Table('table', metadata,
            Column('id', Integer, primary_key=True),
            Column('value', Enum(u'réveillé', u'drôle', u'S’il', name='onetwothreetype'))
        )
        metadata.create_all()
        try:
            t1.insert().execute(value=u'drôle')
            t1.insert().execute(value=u'réveillé')
            t1.insert().execute(value=u'S’il')
            eq_(t1.select().order_by(t1.c.id).execute().fetchall(), 
                [(1, u'drôle'), (2, u'réveillé'), (3, u'S’il')]
            )
            
            m2 = MetaData(testing.db)
            t2 = Table('table', m2, autoload=True)
            assert t2.c.value.type.enums == (u'réveillé', u'drôle', u'S’il')
            
        finally:
            metadata.drop_all()
        
    def test_standalone_enum(self):
        metadata = MetaData(testing.db)
        etype = Enum('four', 'five', 'six', name='fourfivesixtype', metadata=metadata)
        etype.create()
        try:
            assert testing.db.dialect.has_type(testing.db, 'fourfivesixtype')
        finally:
            etype.drop()
            assert not testing.db.dialect.has_type(testing.db, 'fourfivesixtype')
    
        metadata.create_all()
        try:
            assert testing.db.dialect.has_type(testing.db, 'fourfivesixtype')
        finally:
            metadata.drop_all()
            assert not testing.db.dialect.has_type(testing.db, 'fourfivesixtype')
    
    def test_reflection(self):
        metadata = MetaData(testing.db)
        etype = Enum('four', 'five', 'six', name='fourfivesixtype', metadata=metadata)
        t1 = Table('table', metadata,
            Column('id', Integer, primary_key=True),
            Column('value', Enum('one', 'two', 'three', name='onetwothreetype')),
            Column('value2', etype)
        )
        metadata.create_all()
        try:
            m2 = MetaData(testing.db)
            t2 = Table('table', m2, autoload=True)
            assert t2.c.value.type.enums == ('one', 'two', 'three')
            assert t2.c.value.type.name == 'onetwothreetype'
            assert t2.c.value2.type.enums == ('four', 'five', 'six')
            assert t2.c.value2.type.name == 'fourfivesixtype'
        finally:
            metadata.drop_all()

    def test_schema_reflection(self):
        metadata = MetaData(testing.db)
        etype = Enum('four', 'five', 'six', 
                        name='fourfivesixtype', 
                        schema='test_schema', 
                        metadata=metadata)
        t1 = Table('table', metadata,
            Column('id', Integer, primary_key=True),
            Column('value', Enum('one', 'two', 'three', 
                                name='onetwothreetype', schema='test_schema')),
            Column('value2', etype)
        )
        metadata.create_all()
        try:
            m2 = MetaData(testing.db)
            t2 = Table('table', m2, autoload=True)
            assert t2.c.value.type.enums == ('one', 'two', 'three')
            assert t2.c.value.type.name == 'onetwothreetype'
            assert t2.c.value2.type.enums == ('four', 'five', 'six')
            assert t2.c.value2.type.name == 'fourfivesixtype'
            assert t2.c.value2.type.schema == 'test_schema'
        finally:
            metadata.drop_all()
        
        
        
        
class InsertTest(TestBase, AssertsExecutionResults):
    __only_on__ = 'postgresql'

    @classmethod
    def setup_class(cls):
        global metadata
        cls.engine= testing.db
        metadata = MetaData(testing.db)

    def teardown(self):
        metadata.drop_all()
        metadata.tables.clear()
        if self.engine is not testing.db:
            self.engine.dispose()

    def test_compiled_insert(self):
        table = Table('testtable', metadata,
            Column('id', Integer, primary_key=True),
            Column('data', String(30)))

        metadata.create_all()

        ins = table.insert(inline=True, values={'data':bindparam('x')}).compile()
        ins.execute({'x':"five"}, {'x':"seven"})
        assert table.select().execute().fetchall() == [(1, 'five'), (2, 'seven')]

    def test_foreignkey_missing_insert(self):
        t1 = Table('t1', metadata,
            Column('id', Integer, primary_key=True)
        )
        t2 = Table('t2', metadata,
            Column('id', Integer, ForeignKey('t1.id'), primary_key=True)
        )
        metadata.create_all()
        
        # want to ensure that 
        # "null value in column "id" violates not-null constraint" is raised (IntegrityError on psycoopg2,
        # but ProgrammingError on pg8000),
        # and not "ProgrammingError: (ProgrammingError) relation "t2_id_seq" does not exist".
        # the latter corresponds to autoincrement behavior, which is not the case
        # here due to the foreign key.
        for eng in [
            engines.testing_engine(options={'implicit_returning':False}),
            engines.testing_engine(options={'implicit_returning':True}),
        ]:
            assert_raises_message(exc.DBAPIError, "violates not-null constraint", eng.execute, t2.insert())
        
        
    def test_sequence_insert(self):
        table = Table('testtable', metadata,
            Column('id', Integer, Sequence('my_seq'), primary_key=True),
            Column('data', String(30)))
        metadata.create_all()
        self._assert_data_with_sequence(table, "my_seq")

    def test_sequence_returning_insert(self):
        table = Table('testtable', metadata,
            Column('id', Integer, Sequence('my_seq'), primary_key=True),
            Column('data', String(30)))
        metadata.create_all()
        self._assert_data_with_sequence_returning(table, "my_seq")

    def test_opt_sequence_insert(self):
        table = Table('testtable', metadata,
            Column('id', Integer, Sequence('my_seq', optional=True), primary_key=True),
            Column('data', String(30)))
        metadata.create_all()
        self._assert_data_autoincrement(table)

    def test_opt_sequence_returning_insert(self):
        table = Table('testtable', metadata,
            Column('id', Integer, Sequence('my_seq', optional=True), primary_key=True),
            Column('data', String(30)))
        metadata.create_all()
        self._assert_data_autoincrement_returning(table)

    def test_autoincrement_insert(self):
        table = Table('testtable', metadata,
            Column('id', Integer, primary_key=True),
            Column('data', String(30)))
        metadata.create_all()
        self._assert_data_autoincrement(table)

    def test_autoincrement_returning_insert(self):
        table = Table('testtable', metadata,
            Column('id', Integer, primary_key=True),
            Column('data', String(30)))
        metadata.create_all()
        self._assert_data_autoincrement_returning(table)

    def test_noautoincrement_insert(self):
        table = Table('testtable', metadata,
            Column('id', Integer, primary_key=True, autoincrement=False),
            Column('data', String(30)))
        metadata.create_all()
        self._assert_data_noautoincrement(table)

    def _assert_data_autoincrement(self, table):
        self.engine = engines.testing_engine(options={'implicit_returning':False})
        metadata.bind = self.engine

        def go():
            # execute with explicit id
            r = table.insert().execute({'id':30, 'data':'d1'})
            assert r.inserted_primary_key == [30]

            # execute with prefetch id
            r = table.insert().execute({'data':'d2'})
            assert r.inserted_primary_key == [1]

            # executemany with explicit ids
            table.insert().execute({'id':31, 'data':'d3'}, {'id':32, 'data':'d4'})

            # executemany, uses SERIAL
            table.insert().execute({'data':'d5'}, {'data':'d6'})

            # single execute, explicit id, inline
            table.insert(inline=True).execute({'id':33, 'data':'d7'})

            # single execute, inline, uses SERIAL
            table.insert(inline=True).execute({'data':'d8'})

        # note that the test framework doesnt capture the "preexecute" of a seqeuence
        # or default.  we just see it in the bind params.

        self.assert_sql(self.engine, go, [], with_sequences=[
            (
                "INSERT INTO testtable (id, data) VALUES (:id, :data)",
                {'id':30, 'data':'d1'}
            ),
            (
                "INSERT INTO testtable (id, data) VALUES (:id, :data)",
                {'id':1, 'data':'d2'}
            ),
            (
                "INSERT INTO testtable (id, data) VALUES (:id, :data)",
                [{'id':31, 'data':'d3'}, {'id':32, 'data':'d4'}]
            ),
            (
                "INSERT INTO testtable (data) VALUES (:data)",
                [{'data':'d5'}, {'data':'d6'}]
            ),
            (
                "INSERT INTO testtable (id, data) VALUES (:id, :data)",
                [{'id':33, 'data':'d7'}]
            ),
            (
                "INSERT INTO testtable (data) VALUES (:data)",
                [{'data':'d8'}]
            ),
        ])

        assert table.select().execute().fetchall() == [
            (30, 'd1'),
            (1, 'd2'),
            (31, 'd3'),
            (32, 'd4'),
            (2, 'd5'),
            (3, 'd6'),
            (33, 'd7'),
            (4, 'd8'),
        ]
        table.delete().execute()

        # test the same series of events using a reflected
        # version of the table
        m2 = MetaData(self.engine)
        table = Table(table.name, m2, autoload=True)

        def go():
            table.insert().execute({'id':30, 'data':'d1'})
            r = table.insert().execute({'data':'d2'})
            assert r.inserted_primary_key == [5]
            table.insert().execute({'id':31, 'data':'d3'}, {'id':32, 'data':'d4'})
            table.insert().execute({'data':'d5'}, {'data':'d6'})
            table.insert(inline=True).execute({'id':33, 'data':'d7'})
            table.insert(inline=True).execute({'data':'d8'})

        self.assert_sql(self.engine, go, [], with_sequences=[
            (
                "INSERT INTO testtable (id, data) VALUES (:id, :data)",
                {'id':30, 'data':'d1'}
            ),
            (
                "INSERT INTO testtable (id, data) VALUES (:id, :data)",
                {'id':5, 'data':'d2'}
            ),
            (
                "INSERT INTO testtable (id, data) VALUES (:id, :data)",
                [{'id':31, 'data':'d3'}, {'id':32, 'data':'d4'}]
            ),
            (
                "INSERT INTO testtable (data) VALUES (:data)",
                [{'data':'d5'}, {'data':'d6'}]
            ),
            (
                "INSERT INTO testtable (id, data) VALUES (:id, :data)",
                [{'id':33, 'data':'d7'}]
            ),
            (
                "INSERT INTO testtable (data) VALUES (:data)",
                [{'data':'d8'}]
            ),
        ])

        assert table.select().execute().fetchall() == [
            (30, 'd1'),
            (5, 'd2'),
            (31, 'd3'),
            (32, 'd4'),
            (6, 'd5'),
            (7, 'd6'),
            (33, 'd7'),
            (8, 'd8'),
        ]
        table.delete().execute()

    def _assert_data_autoincrement_returning(self, table):
        self.engine = engines.testing_engine(options={'implicit_returning':True})
        metadata.bind = self.engine

        def go():
            # execute with explicit id
            r = table.insert().execute({'id':30, 'data':'d1'})
            assert r.inserted_primary_key == [30]

            # execute with prefetch id
            r = table.insert().execute({'data':'d2'})
            assert r.inserted_primary_key == [1]

            # executemany with explicit ids
            table.insert().execute({'id':31, 'data':'d3'}, {'id':32, 'data':'d4'})

            # executemany, uses SERIAL
            table.insert().execute({'data':'d5'}, {'data':'d6'})

            # single execute, explicit id, inline
            table.insert(inline=True).execute({'id':33, 'data':'d7'})

            # single execute, inline, uses SERIAL
            table.insert(inline=True).execute({'data':'d8'})
        
        self.assert_sql(self.engine, go, [], with_sequences=[
            (
                "INSERT INTO testtable (id, data) VALUES (:id, :data)",
                {'id':30, 'data':'d1'}
            ),
            (
                "INSERT INTO testtable (data) VALUES (:data) RETURNING testtable.id",
                {'data': 'd2'}
            ),
            (
                "INSERT INTO testtable (id, data) VALUES (:id, :data)",
                [{'id':31, 'data':'d3'}, {'id':32, 'data':'d4'}]
            ),
            (
                "INSERT INTO testtable (data) VALUES (:data)",
                [{'data':'d5'}, {'data':'d6'}]
            ),
            (
                "INSERT INTO testtable (id, data) VALUES (:id, :data)",
                [{'id':33, 'data':'d7'}]
            ),
            (
                "INSERT INTO testtable (data) VALUES (:data)",
                [{'data':'d8'}]
            ),
        ])

        assert table.select().execute().fetchall() == [
            (30, 'd1'),
            (1, 'd2'),
            (31, 'd3'),
            (32, 'd4'),
            (2, 'd5'),
            (3, 'd6'),
            (33, 'd7'),
            (4, 'd8'),
        ]
        table.delete().execute()

        # test the same series of events using a reflected
        # version of the table
        m2 = MetaData(self.engine)
        table = Table(table.name, m2, autoload=True)

        def go():
            table.insert().execute({'id':30, 'data':'d1'})
            r = table.insert().execute({'data':'d2'})
            assert r.inserted_primary_key == [5]
            table.insert().execute({'id':31, 'data':'d3'}, {'id':32, 'data':'d4'})
            table.insert().execute({'data':'d5'}, {'data':'d6'})
            table.insert(inline=True).execute({'id':33, 'data':'d7'})
            table.insert(inline=True).execute({'data':'d8'})

        self.assert_sql(self.engine, go, [], with_sequences=[
            (
                "INSERT INTO testtable (id, data) VALUES (:id, :data)",
                {'id':30, 'data':'d1'}
            ),
            (
                "INSERT INTO testtable (data) VALUES (:data) RETURNING testtable.id",
                {'data':'d2'}
            ),
            (
                "INSERT INTO testtable (id, data) VALUES (:id, :data)",
                [{'id':31, 'data':'d3'}, {'id':32, 'data':'d4'}]
            ),
            (
                "INSERT INTO testtable (data) VALUES (:data)",
                [{'data':'d5'}, {'data':'d6'}]
            ),
            (
                "INSERT INTO testtable (id, data) VALUES (:id, :data)",
                [{'id':33, 'data':'d7'}]
            ),
            (
                "INSERT INTO testtable (data) VALUES (:data)",
                [{'data':'d8'}]
            ),
        ])

        assert table.select().execute().fetchall() == [
            (30, 'd1'),
            (5, 'd2'),
            (31, 'd3'),
            (32, 'd4'),
            (6, 'd5'),
            (7, 'd6'),
            (33, 'd7'),
            (8, 'd8'),
        ]
        table.delete().execute()

    def _assert_data_with_sequence(self, table, seqname):
        self.engine = engines.testing_engine(options={'implicit_returning':False})
        metadata.bind = self.engine

        def go():
            table.insert().execute({'id':30, 'data':'d1'})
            table.insert().execute({'data':'d2'})
            table.insert().execute({'id':31, 'data':'d3'}, {'id':32, 'data':'d4'})
            table.insert().execute({'data':'d5'}, {'data':'d6'})
            table.insert(inline=True).execute({'id':33, 'data':'d7'})
            table.insert(inline=True).execute({'data':'d8'})

        self.assert_sql(self.engine, go, [], with_sequences=[
            (
                "INSERT INTO testtable (id, data) VALUES (:id, :data)",
                {'id':30, 'data':'d1'}
            ),
            (
                "INSERT INTO testtable (id, data) VALUES (:id, :data)",
                {'id':1, 'data':'d2'}
            ),
            (
                "INSERT INTO testtable (id, data) VALUES (:id, :data)",
                [{'id':31, 'data':'d3'}, {'id':32, 'data':'d4'}]
            ),
            (
                "INSERT INTO testtable (id, data) VALUES (nextval('%s'), :data)" % seqname,
                [{'data':'d5'}, {'data':'d6'}]
            ),
            (
                "INSERT INTO testtable (id, data) VALUES (:id, :data)",
                [{'id':33, 'data':'d7'}]
            ),
            (
                "INSERT INTO testtable (id, data) VALUES (nextval('%s'), :data)" % seqname,
                [{'data':'d8'}]
            ),
        ])

        assert table.select().execute().fetchall() == [
            (30, 'd1'),
            (1, 'd2'),
            (31, 'd3'),
            (32, 'd4'),
            (2, 'd5'),
            (3, 'd6'),
            (33, 'd7'),
            (4, 'd8'),
        ]

        # cant test reflection here since the Sequence must be
        # explicitly specified

    def _assert_data_with_sequence_returning(self, table, seqname):
        self.engine = engines.testing_engine(options={'implicit_returning':True})
        metadata.bind = self.engine

        def go():
            table.insert().execute({'id':30, 'data':'d1'})
            table.insert().execute({'data':'d2'})
            table.insert().execute({'id':31, 'data':'d3'}, {'id':32, 'data':'d4'})
            table.insert().execute({'data':'d5'}, {'data':'d6'})
            table.insert(inline=True).execute({'id':33, 'data':'d7'})
            table.insert(inline=True).execute({'data':'d8'})

        self.assert_sql(self.engine, go, [], with_sequences=[
            (
                "INSERT INTO testtable (id, data) VALUES (:id, :data)",
                {'id':30, 'data':'d1'}
            ),
            (
                "INSERT INTO testtable (id, data) VALUES (nextval('my_seq'), :data) RETURNING testtable.id",
                {'data':'d2'}
            ),
            (
                "INSERT INTO testtable (id, data) VALUES (:id, :data)",
                [{'id':31, 'data':'d3'}, {'id':32, 'data':'d4'}]
            ),
            (
                "INSERT INTO testtable (id, data) VALUES (nextval('%s'), :data)" % seqname,
                [{'data':'d5'}, {'data':'d6'}]
            ),
            (
                "INSERT INTO testtable (id, data) VALUES (:id, :data)",
                [{'id':33, 'data':'d7'}]
            ),
            (
                "INSERT INTO testtable (id, data) VALUES (nextval('%s'), :data)" % seqname,
                [{'data':'d8'}]
            ),
        ])

        assert table.select().execute().fetchall() == [
            (30, 'd1'),
            (1, 'd2'),
            (31, 'd3'),
            (32, 'd4'),
            (2, 'd5'),
            (3, 'd6'),
            (33, 'd7'),
            (4, 'd8'),
        ]

        # cant test reflection here since the Sequence must be
        # explicitly specified

    def _assert_data_noautoincrement(self, table):
        self.engine = engines.testing_engine(options={'implicit_returning':False})
        metadata.bind = self.engine

        table.insert().execute({'id':30, 'data':'d1'})
        
        if self.engine.driver == 'pg8000':
            exception_cls = exc.ProgrammingError
        else:
            exception_cls = exc.IntegrityError
        
        assert_raises_message(exception_cls, "violates not-null constraint", table.insert().execute, {'data':'d2'})
        assert_raises_message(exception_cls, "violates not-null constraint", table.insert().execute, {'data':'d2'}, {'data':'d3'})

        assert_raises_message(exception_cls, "violates not-null constraint", table.insert().execute, {'data':'d2'})

        assert_raises_message(exception_cls, "violates not-null constraint", table.insert().execute, {'data':'d2'}, {'data':'d3'})

        table.insert().execute({'id':31, 'data':'d2'}, {'id':32, 'data':'d3'})
        table.insert(inline=True).execute({'id':33, 'data':'d4'})

        assert table.select().execute().fetchall() == [
            (30, 'd1'),
            (31, 'd2'),
            (32, 'd3'),
            (33, 'd4'),
        ]
        table.delete().execute()

        # test the same series of events using a reflected
        # version of the table
        m2 = MetaData(self.engine)
        table = Table(table.name, m2, autoload=True)
        table.insert().execute({'id':30, 'data':'d1'})

        assert_raises_message(exception_cls, "violates not-null constraint", table.insert().execute, {'data':'d2'})
        assert_raises_message(exception_cls, "violates not-null constraint", table.insert().execute, {'data':'d2'}, {'data':'d3'})

        table.insert().execute({'id':31, 'data':'d2'}, {'id':32, 'data':'d3'})
        table.insert(inline=True).execute({'id':33, 'data':'d4'})

        assert table.select().execute().fetchall() == [
            (30, 'd1'),
            (31, 'd2'),
            (32, 'd3'),
            (33, 'd4'),
        ]

class DomainReflectionTest(TestBase, AssertsExecutionResults):
    "Test PostgreSQL domains"

    __only_on__ = 'postgresql'

    @classmethod
    def setup_class(cls):
        con = testing.db.connect()
        for ddl in ('CREATE DOMAIN testdomain INTEGER NOT NULL DEFAULT 42',
                    'CREATE DOMAIN test_schema.testdomain INTEGER DEFAULT 0'):
            try:
                con.execute(ddl)
            except exc.SQLError, e:
                if not "already exists" in str(e):
                    raise e
        con.execute('CREATE TABLE testtable (question integer, answer testdomain)')
        con.execute('CREATE TABLE test_schema.testtable(question integer, answer test_schema.testdomain, anything integer)')
        con.execute('CREATE TABLE crosschema (question integer, answer test_schema.testdomain)')

    @classmethod
    def teardown_class(cls):
        con = testing.db.connect()
        con.execute('DROP TABLE testtable')
        con.execute('DROP TABLE test_schema.testtable')
        con.execute('DROP TABLE crosschema')
        con.execute('DROP DOMAIN testdomain')
        con.execute('DROP DOMAIN test_schema.testdomain')

    def test_table_is_reflected(self):
        metadata = MetaData(testing.db)
        table = Table('testtable', metadata, autoload=True)
        eq_(set(table.columns.keys()), set(['question', 'answer']), "Columns of reflected table didn't equal expected columns")
        assert isinstance(table.c.answer.type, Integer)

    def test_domain_is_reflected(self):
        metadata = MetaData(testing.db)
        table = Table('testtable', metadata, autoload=True)
        eq_(str(table.columns.answer.server_default.arg), '42', "Reflected default value didn't equal expected value")
        assert not table.columns.answer.nullable, "Expected reflected column to not be nullable."

    def test_table_is_reflected_test_schema(self):
        metadata = MetaData(testing.db)
        table = Table('testtable', metadata, autoload=True, schema='test_schema')
        eq_(set(table.columns.keys()), set(['question', 'answer', 'anything']), "Columns of reflected table didn't equal expected columns")
        assert isinstance(table.c.anything.type, Integer)

    def test_schema_domain_is_reflected(self):
        metadata = MetaData(testing.db)
        table = Table('testtable', metadata, autoload=True, schema='test_schema')
        eq_(str(table.columns.answer.server_default.arg), '0', "Reflected default value didn't equal expected value")
        assert table.columns.answer.nullable, "Expected reflected column to be nullable."

    def test_crosschema_domain_is_reflected(self):
        metadata = MetaData(testing.db)
        table = Table('crosschema', metadata, autoload=True)
        eq_(str(table.columns.answer.server_default.arg), '0', "Reflected default value didn't equal expected value")
        assert table.columns.answer.nullable, "Expected reflected column to be nullable."

    def test_unknown_types(self):
        from sqlalchemy.databases import postgresql

        ischema_names = postgresql.PGDialect.ischema_names
        postgresql.PGDialect.ischema_names = {}
        try:
            m2 = MetaData(testing.db)
            assert_raises(exc.SAWarning, Table, "testtable", m2, autoload=True)

            @testing.emits_warning('Did not recognize type')
            def warns():
                m3 = MetaData(testing.db)
                t3 = Table("testtable", m3, autoload=True)
                assert t3.c.answer.type.__class__ == sa.types.NullType

        finally:
            postgresql.PGDialect.ischema_names = ischema_names


class MiscTest(TestBase, AssertsExecutionResults, AssertsCompiledSQL):
    __only_on__ = 'postgresql'

    def test_date_reflection(self):
        m1 = MetaData(testing.db)
        t1 = Table('pgdate', m1,
            Column('date1', DateTime(timezone=True)),
            Column('date2', DateTime(timezone=False))
            )
        m1.create_all()
        try:
            m2 = MetaData(testing.db)
            t2 = Table('pgdate', m2, autoload=True)
            assert t2.c.date1.type.timezone is True
            assert t2.c.date2.type.timezone is False
        finally:
            m1.drop_all()

    def test_pg_weirdchar_reflection(self):
        meta1 = MetaData(testing.db)
        subject = Table("subject", meta1,
                        Column("id$", Integer, primary_key=True),
                        )

        referer = Table("referer", meta1,
                        Column("id", Integer, primary_key=True),
                        Column("ref", Integer, ForeignKey('subject.id$')),
                        )
        meta1.create_all()
        try:
            meta2 = MetaData(testing.db)
            subject = Table("subject", meta2, autoload=True)
            referer = Table("referer", meta2, autoload=True)
            print str(subject.join(referer).onclause)
            self.assert_((subject.c['id$']==referer.c.ref).compare(subject.join(referer).onclause))
        finally:
            meta1.drop_all()

    def test_checksfor_sequence(self):
        meta1 = MetaData(testing.db)
        t = Table('mytable', meta1,
            Column('col1', Integer, Sequence('fooseq')))
        try:
            testing.db.execute("CREATE SEQUENCE fooseq")
            t.create(checkfirst=True)
        finally:
            t.drop(checkfirst=True)

    def test_distinct_on(self):
        t = Table('mytable', MetaData(testing.db),
                  Column('id', Integer, primary_key=True),
                  Column('a', String(8)))
        eq_(
            str(t.select(distinct=t.c.a)),
            'SELECT DISTINCT ON (mytable.a) mytable.id, mytable.a \n'
            'FROM mytable')
        eq_(
            str(t.select(distinct=['id','a'])),
            'SELECT DISTINCT ON (id, a) mytable.id, mytable.a \n'
            'FROM mytable')
        eq_(
            str(t.select(distinct=[t.c.id, t.c.a])),
            'SELECT DISTINCT ON (mytable.id, mytable.a) mytable.id, mytable.a \n'
            'FROM mytable')

    def test_schema_reflection(self):
        """note: this test requires that the 'test_schema' schema be separate and accessible by the test user"""

        meta1 = MetaData(testing.db)
        users = Table('users', meta1,
            Column('user_id', Integer, primary_key = True),
            Column('user_name', String(30), nullable = False),
            schema="test_schema"
            )

        addresses = Table('email_addresses', meta1,
            Column('address_id', Integer, primary_key = True),
            Column('remote_user_id', Integer, ForeignKey(users.c.user_id)),
            Column('email_address', String(20)),
            schema="test_schema"
        )
        meta1.create_all()
        try:
            meta2 = MetaData(testing.db)
            addresses = Table('email_addresses', meta2, autoload=True, schema="test_schema")
            users = Table('users', meta2, mustexist=True, schema="test_schema")

            print users
            print addresses
            j = join(users, addresses)
            print str(j.onclause)
            self.assert_((users.c.user_id==addresses.c.remote_user_id).compare(j.onclause))
        finally:
            meta1.drop_all()

    def test_schema_reflection_2(self):
        meta1 = MetaData(testing.db)
        subject = Table("subject", meta1,
                        Column("id", Integer, primary_key=True),
                        )

        referer = Table("referer", meta1,
                        Column("id", Integer, primary_key=True),
                        Column("ref", Integer, ForeignKey('subject.id')),
                        schema="test_schema")
        meta1.create_all()
        try:
            meta2 = MetaData(testing.db)
            subject = Table("subject", meta2, autoload=True)
            referer = Table("referer", meta2, schema="test_schema", autoload=True)
            print str(subject.join(referer).onclause)
            self.assert_((subject.c.id==referer.c.ref).compare(subject.join(referer).onclause))
        finally:
            meta1.drop_all()

    def test_schema_reflection_3(self):
        meta1 = MetaData(testing.db)
        subject = Table("subject", meta1,
                        Column("id", Integer, primary_key=True),
                        schema='test_schema_2'
                        )

        referer = Table("referer", meta1,
                        Column("id", Integer, primary_key=True),
                        Column("ref", Integer, ForeignKey('test_schema_2.subject.id')),
                        schema="test_schema")

        meta1.create_all()
        try:
            meta2 = MetaData(testing.db)
            subject = Table("subject", meta2, autoload=True, schema="test_schema_2")
            referer = Table("referer", meta2, schema="test_schema", autoload=True)
            print str(subject.join(referer).onclause)
            self.assert_((subject.c.id==referer.c.ref).compare(subject.join(referer).onclause))
        finally:
            meta1.drop_all()

    def test_schema_roundtrips(self):
        meta = MetaData(testing.db)
        users = Table('users', meta,
            Column('id', Integer, primary_key=True),
            Column('name', String(50)), schema='test_schema')
        users.create()
        try:
            users.insert().execute(id=1, name='name1')
            users.insert().execute(id=2, name='name2')
            users.insert().execute(id=3, name='name3')
            users.insert().execute(id=4, name='name4')

            eq_(users.select().where(users.c.name=='name2').execute().fetchall(), [(2, 'name2')])
            eq_(users.select(use_labels=True).where(users.c.name=='name2').execute().fetchall(), [(2, 'name2')])

            users.delete().where(users.c.id==3).execute()
            eq_(users.select().where(users.c.name=='name3').execute().fetchall(), [])

            users.update().where(users.c.name=='name4').execute(name='newname')
            eq_(users.select(use_labels=True).where(users.c.id==4).execute().fetchall(), [(4, 'newname')])

        finally:
            users.drop()

    def test_preexecute_passivedefault(self):
        """test that when we get a primary key column back
        from reflecting a table which has a default value on it, we pre-execute
        that DefaultClause upon insert."""

        try:
            meta = MetaData(testing.db)
            testing.db.execute("""
             CREATE TABLE speedy_users
             (
                 speedy_user_id   SERIAL     PRIMARY KEY,

                 user_name        VARCHAR    NOT NULL,
                 user_password    VARCHAR    NOT NULL
             );
            """)

            t = Table("speedy_users", meta, autoload=True)
            r = t.insert().execute(user_name='user', user_password='lala')
            assert r.inserted_primary_key == [1]
            l = t.select().execute().fetchall()
            assert l == [(1, 'user', 'lala')]
        finally:
            testing.db.execute("drop table speedy_users")

    @testing.emits_warning()
    def test_index_reflection(self):
        """ Reflecting partial & expression-based indexes should warn """
        import warnings
        def capture_warnings(*args, **kw):
            capture_warnings._orig_showwarning(*args, **kw)
            capture_warnings.warnings.append(args)
        capture_warnings._orig_showwarning = warnings.warn
        capture_warnings.warnings = []

        m1 = MetaData(testing.db)
        t1 = Table('party', m1,
            Column('id', String(10), nullable=False),
            Column('name', String(20), index=True), 
            Column('aname', String(20))
            )
        m1.create_all()
        
        testing.db.execute("""
          create index idx1 on party ((id || name))
        """) 
        testing.db.execute("""
          create unique index idx2 on party (id) where name = 'test'
        """)
        
        testing.db.execute("""
            create index idx3 on party using btree
                (lower(name::text), lower(aname::text))
        """)
        
        try:
            m2 = MetaData(testing.db)

            warnings.warn = capture_warnings
            t2 = Table('party', m2, autoload=True)
      
            wrn = capture_warnings.warnings
            assert str(wrn[0][0]) == (
              "Skipped unsupported reflection of expression-based index idx1")
            assert str(wrn[1][0]) == (
              "Predicate of partial index idx2 ignored during reflection")
            assert len(t2.indexes) == 2
            # Make sure indexes are in the order we expect them in
            tmp = [(idx.name, idx) for idx in t2.indexes]
            tmp.sort()
            
            r1, r2 = [idx[1] for idx in tmp]

            assert r1.name == 'idx2'
            assert r1.unique == True
            assert r2.unique == False
            assert [t2.c.id] == r1.columns
            assert [t2.c.name] == r2.columns
        finally:
            warnings.warn = capture_warnings._orig_showwarning
            m1.drop_all()

    def test_set_isolation_level(self):
        """Test setting the isolation level with create_engine"""
        eng = create_engine(testing.db.url)
        eq_(
            eng.execute("show transaction isolation level").scalar(),
            'read committed')
        eng = create_engine(testing.db.url, isolation_level="SERIALIZABLE")
        eq_(
            eng.execute("show transaction isolation level").scalar(),
            'serializable')
        eng = create_engine(testing.db.url, isolation_level="FOO")

        if testing.db.driver == 'zxjdbc':
            exception_cls = eng.dialect.dbapi.Error
        else:
            exception_cls = eng.dialect.dbapi.ProgrammingError
        assert_raises(exception_cls, eng.execute, "show transaction isolation level")


class TimezoneTest(TestBase, AssertsExecutionResults):
    """Test timezone-aware datetimes.

    psycopg will return a datetime with a tzinfo attached to it, if postgresql
    returns it.  python then will not let you compare a datetime with a tzinfo
    to a datetime that doesnt have one.  this test illustrates two ways to
    have datetime types with and without timezone info.
    """

    __only_on__ = 'postgresql'

    @classmethod
    def setup_class(cls):
        global tztable, notztable, metadata
        metadata = MetaData(testing.db)

        # current_timestamp() in postgresql is assumed to return TIMESTAMP WITH TIMEZONE
        tztable = Table('tztable', metadata,
            Column("id", Integer, primary_key=True),
            Column("date", DateTime(timezone=True), onupdate=func.current_timestamp()),
            Column("name", String(20)),
        )
        notztable = Table('notztable', metadata,
            Column("id", Integer, primary_key=True),
            Column("date", DateTime(timezone=False), onupdate=cast(func.current_timestamp(), DateTime(timezone=False))),
            Column("name", String(20)),
        )
        metadata.create_all()
    @classmethod
    def teardown_class(cls):
        metadata.drop_all()

    def test_with_timezone(self):
        # get a date with a tzinfo
        somedate = testing.db.connect().scalar(func.current_timestamp().select())
        tztable.insert().execute(id=1, name='row1', date=somedate)
        c = tztable.update(tztable.c.id==1).execute(name='newname')
        print tztable.select(tztable.c.id==1).execute().first()

    def test_without_timezone(self):
        # get a date without a tzinfo
        somedate = datetime.datetime(2005, 10,20, 11, 52, 00)
        notztable.insert().execute(id=1, name='row1', date=somedate)
        c = notztable.update(notztable.c.id==1).execute(name='newname')
        print notztable.select(tztable.c.id==1).execute().first()

class ArrayTest(TestBase, AssertsExecutionResults):
    __only_on__ = 'postgresql'

    @classmethod
    def setup_class(cls):
        global metadata, arrtable
        metadata = MetaData(testing.db)

        arrtable = Table('arrtable', metadata,
            Column('id', Integer, primary_key=True),
            Column('intarr', postgresql.PGArray(Integer)),
            Column('strarr', postgresql.PGArray(Unicode(assert_unicode=False)), nullable=False)
        )
        metadata.create_all()

    def teardown(self):
        arrtable.delete().execute()
        
    @classmethod
    def teardown_class(cls):
        metadata.drop_all()

    def test_reflect_array_column(self):
        metadata2 = MetaData(testing.db)
        tbl = Table('arrtable', metadata2, autoload=True)
        assert isinstance(tbl.c.intarr.type, postgresql.PGArray)
        assert isinstance(tbl.c.strarr.type, postgresql.PGArray)
        assert isinstance(tbl.c.intarr.type.item_type, Integer)
        assert isinstance(tbl.c.strarr.type.item_type, String)

    @testing.fails_on('postgresql+zxjdbc', 'zxjdbc has no support for PG arrays')
    def test_insert_array(self):
        arrtable.insert().execute(intarr=[1,2,3], strarr=['abc', 'def'])
        results = arrtable.select().execute().fetchall()
        eq_(len(results), 1)
        eq_(results[0]['intarr'], [1,2,3])
        eq_(results[0]['strarr'], ['abc','def'])

    @testing.fails_on('postgresql+pg8000', 'pg8000 has poor support for PG arrays')
    @testing.fails_on('postgresql+zxjdbc', 'zxjdbc has no support for PG arrays')
    def test_array_where(self):
        arrtable.insert().execute(intarr=[1,2,3], strarr=['abc', 'def'])
        arrtable.insert().execute(intarr=[4,5,6], strarr='ABC')
        results = arrtable.select().where(arrtable.c.intarr == [1,2,3]).execute().fetchall()
        eq_(len(results), 1)
        eq_(results[0]['intarr'], [1,2,3])

    @testing.fails_on('postgresql+pg8000', 'pg8000 has poor support for PG arrays')
    @testing.fails_on('postgresql+zxjdbc', 'zxjdbc has no support for PG arrays')
    def test_array_concat(self):
        arrtable.insert().execute(intarr=[1,2,3], strarr=['abc', 'def'])
        results = select([arrtable.c.intarr + [4,5,6]]).execute().fetchall()
        eq_(len(results), 1)
        eq_(results[0][0], [1,2,3,4,5,6])

    @testing.fails_on('postgresql+pg8000', 'pg8000 has poor support for PG arrays')
    @testing.fails_on('postgresql+zxjdbc', 'zxjdbc has no support for PG arrays')
    def test_array_subtype_resultprocessor(self):
        arrtable.insert().execute(intarr=[4,5,6], strarr=[[u'm\xe4\xe4'], [u'm\xf6\xf6']])
        arrtable.insert().execute(intarr=[1,2,3], strarr=[u'm\xe4\xe4', u'm\xf6\xf6'])
        results = arrtable.select(order_by=[arrtable.c.intarr]).execute().fetchall()
        eq_(len(results), 2)
        eq_(results[0]['strarr'], [u'm\xe4\xe4', u'm\xf6\xf6'])
        eq_(results[1]['strarr'], [[u'm\xe4\xe4'], [u'm\xf6\xf6']])

    @testing.fails_on('postgresql+pg8000', 'pg8000 has poor support for PG arrays')
    @testing.fails_on('postgresql+zxjdbc', 'zxjdbc has no support for PG arrays')
    def test_array_mutability(self):
        class Foo(object): pass
        footable = Table('foo', metadata,
            Column('id', Integer, primary_key=True),
            Column('intarr', postgresql.PGArray(Integer), nullable=True)
        )
        mapper(Foo, footable)
        metadata.create_all()
        sess = create_session()

        foo = Foo()
        foo.id = 1
        foo.intarr = [1,2,3]
        sess.add(foo)
        sess.flush()
        sess.expunge_all()
        foo = sess.query(Foo).get(1)
        eq_(foo.intarr, [1,2,3])

        foo.intarr.append(4)
        sess.flush()
        sess.expunge_all()
        foo = sess.query(Foo).get(1)
        eq_(foo.intarr, [1,2,3,4])

        foo.intarr = []
        sess.flush()
        sess.expunge_all()
        eq_(foo.intarr, [])

        foo.intarr = None
        sess.flush()
        sess.expunge_all()
        eq_(foo.intarr, None)

        # Errors in r4217:
        foo = Foo()
        foo.id = 2
        sess.add(foo)
        sess.flush()

class TimestampTest(TestBase, AssertsExecutionResults):
    __only_on__ = 'postgresql'

    def test_timestamp(self):
        engine = testing.db
        connection = engine.connect()
        
        s = select(["timestamp '2007-12-25'"])
        result = connection.execute(s).first()
        eq_(result[0], datetime.datetime(2007, 12, 25, 0, 0))

class ServerSideCursorsTest(TestBase, AssertsExecutionResults):
    __only_on__ = 'postgresql+psycopg2'

    @classmethod
    def setup_class(cls):
        global ss_engine
        ss_engine = engines.testing_engine(options={'server_side_cursors':True})

    @classmethod
    def teardown_class(cls):
        ss_engine.dispose()

    def test_uses_ss(self):
        result = ss_engine.execute("select 1")
        assert result.cursor.name
        
        result = ss_engine.execute(text("select 1"))
        assert result.cursor.name

        result = ss_engine.execute(select([1]))
        assert result.cursor.name
        
    def test_roundtrip(self):
        test_table = Table('test_table', MetaData(ss_engine),
            Column('id', Integer, primary_key=True),
            Column('data', String(50))
        )
        test_table.create(checkfirst=True)
        try:
            test_table.insert().execute(data='data1')

            nextid = ss_engine.execute(Sequence('test_table_id_seq'))
            test_table.insert().execute(id=nextid, data='data2')

            eq_(test_table.select().execute().fetchall(), [(1, 'data1'), (2, 'data2')])

            test_table.update().where(test_table.c.id==2).values(data=test_table.c.data + ' updated').execute()
            eq_(test_table.select().execute().fetchall(), [(1, 'data1'), (2, 'data2 updated')])
            test_table.delete().execute()
            eq_(test_table.count().scalar(), 0)
        finally:
            test_table.drop(checkfirst=True)

class SpecialTypesTest(TestBase, ComparesTables):
    """test DDL and reflection of PG-specific types """
    
    __only_on__ = 'postgresql'
    __excluded_on__ = (('postgresql', '<', (8, 3, 0)),)
    
    @classmethod
    def setup_class(cls):
        global metadata, table
        metadata = MetaData(testing.db)
        
        table = Table('sometable', metadata,
            Column('id', postgresql.PGUuid, primary_key=True),
            Column('flag', postgresql.PGBit),
            Column('addr', postgresql.PGInet),
            Column('addr2', postgresql.PGMacAddr),
            Column('addr3', postgresql.PGCidr),
            Column('doubleprec', postgresql.DOUBLE_PRECISION)
            
        )
        
        metadata.create_all()
    
    @classmethod
    def teardown_class(cls):
        metadata.drop_all()
    
    def test_reflection(self):
        m = MetaData(testing.db)
        t = Table('sometable', m, autoload=True)
        
        self.assert_tables_equal(table, t, strict_types=True)
        

class MatchTest(TestBase, AssertsCompiledSQL):
    __only_on__ = 'postgresql'
    __excluded_on__ = (('postgresql', '<', (8, 3, 0)),)

    @classmethod
    def setup_class(cls):
        global metadata, cattable, matchtable
        metadata = MetaData(testing.db)

        cattable = Table('cattable', metadata,
            Column('id', Integer, primary_key=True),
            Column('description', String(50)),
        )
        matchtable = Table('matchtable', metadata,
            Column('id', Integer, primary_key=True),
            Column('title', String(200)),
            Column('category_id', Integer, ForeignKey('cattable.id')),
        )
        metadata.create_all()

        cattable.insert().execute([
            {'id': 1, 'description': 'Python'},
            {'id': 2, 'description': 'Ruby'},
        ])
        matchtable.insert().execute([
            {'id': 1, 'title': 'Agile Web Development with Rails', 'category_id': 2},
            {'id': 2, 'title': 'Dive Into Python', 'category_id': 1},
            {'id': 3, 'title': 'Programming Matz''s Ruby', 'category_id': 2},
            {'id': 4, 'title': 'The Definitive Guide to Django', 'category_id': 1},
            {'id': 5, 'title': 'Python in a Nutshell', 'category_id': 1}
        ])

    @classmethod
    def teardown_class(cls):
        metadata.drop_all()

    @testing.fails_on('postgresql+pg8000', 'uses positional')
    @testing.fails_on('postgresql+zxjdbc', 'uses qmark')
    def test_expression_pyformat(self):
        self.assert_compile(matchtable.c.title.match('somstr'), "matchtable.title @@ to_tsquery(%(title_1)s)")

    @testing.fails_on('postgresql+psycopg2', 'uses pyformat')
    @testing.fails_on('postgresql+zxjdbc', 'uses qmark')
    def test_expression_positional(self):
        self.assert_compile(matchtable.c.title.match('somstr'), "matchtable.title @@ to_tsquery(%s)")

    def test_simple_match(self):
        results = matchtable.select().where(matchtable.c.title.match('python')).order_by(matchtable.c.id).execute().fetchall()
        eq_([2, 5], [r.id for r in results])

    def test_simple_match_with_apostrophe(self):
        results = matchtable.select().where(matchtable.c.title.match("Matz''s")).execute().fetchall()
        eq_([3], [r.id for r in results])

    def test_simple_derivative_match(self):
        results = matchtable.select().where(matchtable.c.title.match('nutshells')).execute().fetchall()
        eq_([5], [r.id for r in results])

    def test_or_match(self):
        results1 = matchtable.select().where(or_(matchtable.c.title.match('nutshells'), 
                                                 matchtable.c.title.match('rubies'))
                                            ).order_by(matchtable.c.id).execute().fetchall()
        eq_([3, 5], [r.id for r in results1])
        results2 = matchtable.select().where(matchtable.c.title.match('nutshells | rubies'), 
                                            ).order_by(matchtable.c.id).execute().fetchall()
        eq_([3, 5], [r.id for r in results2])
        

    def test_and_match(self):
        results1 = matchtable.select().where(and_(matchtable.c.title.match('python'), 
                                                  matchtable.c.title.match('nutshells'))
                                            ).execute().fetchall()
        eq_([5], [r.id for r in results1])
        results2 = matchtable.select().where(matchtable.c.title.match('python & nutshells'), 
                                            ).execute().fetchall()
        eq_([5], [r.id for r in results2])

    def test_match_across_joins(self):
        results = matchtable.select().where(and_(cattable.c.id==matchtable.c.category_id, 
                                            or_(cattable.c.description.match('Ruby'), 
                                                matchtable.c.title.match('nutshells')))
                                           ).order_by(matchtable.c.id).execute().fetchall()
        eq_([1, 3, 5], [r.id for r in results])


