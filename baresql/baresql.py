# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals, division # Python2.7
import re
import numbers
import sqlite3 as sqlite
import sys
import os
import locale
import csv
import datetime
import io
import codecs
import shlex  # Simple lexical analysis

import numpy as np
import pandas as pd
from distutils.version import LooseVersion, StrictVersion
try:
    from pandas.io.sql import to_sql, execute
except: #pandas older version
    from pandas.io.sql import write_frame, execute
    to_sql = write_frame 
#see http://stackoverflow.com/questions/17053435/mysql-connector-python-insert-python-variable-to-mysql-table
try:
    import mysql.connector
    #create numpy compatibility
    class NumpyMySQLConverter(mysql.connector.conversion.MySQLConverter):
        """ A mysql.connector Converter that handles Numpy types """

        def _float32_to_mysql(self, value):
            return float(value)

        def _float64_to_mysql(self, value):
            return float(value)

        def _int32_to_mysql(self, value):
            return int(value)

        def _int64_to_mysql(self, value):
            return int(value)
except:
    pass

class baresql(object):
    """
    baresql allows you to query in sql any of your python datas.
    
    In the sql :
     - use 'table$$' to temporary upload a  python 'table',
     - use ':variable' to refer to a  python 'variable',
          ('%(variable)s' if you employ mysql)
     - use 'PERSIST table' to upload and keep given Python table

    Typical syntax : "select * from users$$ where c0 <= :limit"
                  or "persist users;select * from users where c0 <= :limit" 

    Output of a query can be obtained as :
     - a pandas dataframe (bsql.df)
     - a list of rows (bsql.rows)
     - a list of 1 column (bsql.column) (first column by default)
     - a sql cursor (bsql.cursor) (not recommanded)

    Complementary features :
     - multiple sql actions can be executed in the same request,
     - mixing sql tables and python tables in a sql request.

    Example :
        #initialisation
        from baresql import baresql 
        bsql=baresql()  
        bsqldf = lambda q: bsql.df(q, dict(globals(),**locals()))

        #create some python datas
        users = [(i, "user N°"+str(i)) for i in range(7)]
        limit = 4 

        #sql query on those datas
        print(bsqldf("select * from users$$ where c0 <= :limit"))

        #same with a mysql server
        cnx = mysql.connector.connect(**config)
        bsql = baresql(cnx)

        print(bsqldf("select   * from users$$ where c0 <= %(limit)s"))

        #pydef function (if Sqlite motor only, beware output are always strings)
        bsqldf("pydef py_quad(s): return ('%s' %  float(s)**4);;")
        bsqldf("select py_quad(2)")

    baresql re-use or re-implement parts of the code of 
       . github.com/yhat/pandasql (MIT licence, Copyright 2013 Yhat, Inc)
       . github.com/pydata/pandas (BSD simplified licence
       Copyright 2011-2012, Lambda Foundry, Inc. and PyData Development Team)
    """

    def __init__(self, connection="sqlite://", keep_log = False, cte_inline=False,
                 isolation_level=None):
        """
        conn = connection string  , or connexion object if mysql
          example :
            "sqlite://" = sqlite in memory
            "sqlite:///.baresql.db" = sqlite on disk database ".baresql.db"
        keep_log = keep log of SQL instructions generated
        """
        self.__version__ = '0.8.0'
        self._title = "2023-05-20 : 'np.float becomes float'"
        #identify sql engine and database
        self.connection = connection
        if isinstance(self.connection, (type(u'a') , type('a'))):
           self.engine = connection.split("://")[0]
           if self.engine == "sqlite" or self.engine == "mysql":
              self.dbname = "/".join(((connection+"").split("/")[3:]))
              if  self.dbname.strip() == "":
                  self.dbname = ":memory:"
           else:
               print (self.engine)
               raise Exception("Only sqlite and mysql are supported yet") 

           #realize connexion
           self.conn = sqlite.connect(self.dbname, 
                                      detect_types = sqlite.PARSE_DECLTYPES)
        else: #we suppose "mysql", if it is a connexion object
            self.conn=self.connection
            self.engine="mysql"

        self.tmp_tables = []

        #pydef memory
        self.conn_def = {}
        
        #logging infrastructure
        self.do_log = keep_log
        self.log = []

        #check if need cte_helper
        self.delimiters=['[',']']
        
        if  self.engine == "mysql":
            self.delimiters=['`','`']
            #http://stackoverflow.com/questions/17053435/mysql-connector-python-insert-python-variable-to-mysql-table
            try:
                self.conn.set_converter_class(NumpyMySQLConverter)
            except:
                pass
        if  self.engine == "sqlite":
            cur=execute("select  sqlite_version()" ,self.conn)
            version = cur.fetchall()[0][0]
            cur.close
            normalized=".".join( [("000"+i)[-3:] for i in version.split("." )]) 

    def close(self):
        "proper closing"
        self.remove_tmp_tables
        self.conn.close


    def remove_tmp_tables(self, origin="all"):
        "remove temporarly created tables"
        if origin in ("all", "tmp"):
            for table in self.tmp_tables:
                cur = self._execute_sql("DROP TABLE IF EXISTS %s" %
                                        table.join(self.delimiters))
            self.tmp_tables = []
            

    def get_tokens(self, sql, start=0, shell_tokens=False):
        """
        from given sql start position, yield tokens (value + token type)
        if shell_tokens is True, identify line shell_tokens as sqlite.exe does
        """
        length = len(sql)
        i = start
        can_be_shell_command = True
        dico = {' ': 'TK_SP', '\t': 'TK_SP', '\n': 'TK_SP', '\f': 'TK_SP',
                '\r': 'TK_SP', '(': 'TK_LP', ')': 'TK_RP', ';': 'TK_SEMI',
                ',': 'TK_COMMA', '/': 'TK_OTHER', "'": 'TK_STRING',
                "-": 'TK_OTHER', '"': 'TK_STRING', "`": 'TK_STRING'}
        while length > start:
            token = 'TK_OTHER'
            if shell_tokens and can_be_shell_command and i < length and (
               (sql[i] == "." and i == start) or
               (i > start and sql[i-1:i] == "\n.")):
                # a command line shell ! (supposed on one starting line)
                token = 'TK_SHELL'
                i = sql.find("\n", start)
                if i <= 0:
                    i = length
            elif sql[i] == "-" and i < length and sql[i:i+2] == "--":
                # this Token is an end-of-line comment : --blabla
                token = 'TK_COM'
                i = sql.find("\n", start)
                if i <= 0:
                    i = length
            elif sql[i] == "/" and i < length and sql[i:i+2] == "/*":
                # this Token is a comment block : /* and bla bla \n bla */
                token = 'TK_COM'
                i = sql.find("*/", start) + 2
                if i <= 1:
                    i = length
            elif sql[i] not in dico:
                # this token is a distinct word (tagged as 'TK_OTHER')
                while i < length and sql[i] not in dico:
                    i += 1
            else:
                # default token analyze case
                token = dico[sql[i]]
                if token == 'TK_SP':
                    # find the end of the 'Spaces' Token just detected
                    while (i < length and sql[i] in dico and
                            dico[sql[i]] == 'TK_SP'):
                                i += 1
                elif token == 'TK_STRING':
                    # find the end of the 'String' Token just detected
                    delimiter = sql[i]
                    if delimiter != "'":
                        token = 'TK_ID'  # usefull nuance ?
                    while(i < length):
                        i = sql.find(delimiter, i+1)
                        if i <= 0:  # String is never closed
                            i = length
                            token = 'TK_ERROR'
                        elif i < length - 1 and sql[i+1] == delimiter:
                            i += 1  # double '' case, so ignore and continue
                        else:
                            i += 1
                            break  # normal End of a  String
                else:
                    if i < length:
                        i += 1
            yield sql[start:i], token
            if token == 'TK_SEMI':  # a new sql order can be a new shell token
                can_be_shell_command = True
            elif token not in ('TK_COM', 'TK_SP'):  # can't be a shell token
                can_be_shell_command = False
            start = i


    def get_sqlsplit(self, sql, remove_comments=False):
        """yield a list of separated sql orders from a sql file"""
        trigger_mode = False
        mysql = [""]
        for tokv, token in self.get_tokens(sql, shell_tokens=True):
            # clear comments option
            if token != 'TK_COM' or not remove_comments:
                mysql.append(tokv)
            # special case for Trigger : semicolumn don't count
            if token == 'TK_OTHER':
                tok = tokv.upper()
                if tok == "TRIGGER":
                    trigger_mode = True
                    translvl = 0
                elif trigger_mode and tok in('BEGIN', 'CASE'):
                    translvl += 1
                elif trigger_mode and tok == 'END':
                    translvl -= 1
                    if translvl <= 0:
                        trigger_mode = False
            elif (token == 'TK_SEMI' and not trigger_mode):
                # end of a single sql
                yield "".join(mysql)
                mysql = []
            elif (token == 'TK_SHELL'):
                # end of a shell order
                yield("" + tokv)
                mysql = []
        if mysql != []:
            yield("".join(mysql))
        
             
    def _execute_sql(self, q_in ,  env = None):
        "execute sql but intercept log"
        if self.do_log:
            self.log.append(q_in)
        env_final = env
        if isinstance(env, (list,tuple)) and len(env)>0 and isinstance(env[-1], dict):
            env_final = env[:-1] #remove last dict(), if parameters list
        if self.engine=="mysql" and isinstance(env, dict):
            #we must clean from what is not used
            env_final={k:v for k,v in env_final.items() if "%("+k+")s" in q_in}
        return execute(q_in ,self.conn, params = env_final)


    def _execute_cte(self, q_in,  env):
        """transform Common Table Expression SQL into acceptable SQLite SQLs
           with w    as (y) z => create w as y;z
           with w(x) as (y) z => create w(x);insert into w y;z
        """
        q_raw = q_in.strip()
        #normal execute
        return self._execute_sql(q_raw,env)


    def _ensure_data_frame(self, obj, name):
        """
        obj a python object to be converted to a DataFrame
        take an object and make sure that it's a pandas data frame
        """
        #we accept pandas Dataframe, and also dictionaries, lists, tuples
        #we'll just convert them to Pandas Dataframe
        if isinstance(obj, pd.DataFrame):
            df = obj
        elif isinstance(obj, (tuple, list, range)) :
            #tuple and list case
            if len(obj) == 0:
                return pd.Dataframe()

            firstrow = obj[0]

            if isinstance(firstrow, (tuple, list)):
                #multiple-columns
                colnames = ["c%d" % i for i in range(len(firstrow))]
                df = pd.DataFrame(obj, columns=colnames)
            else:
                #mono-column
                df = pd.DataFrame(list(obj), columns = ["c0"])
        elif isinstance(obj, dict) :
            #dictionary case
            df = pd.DataFrame([(k,v) for k, v in obj.items()],
                               columns = ["c0","c1"])
        elif isinstance(obj, (type('a'),type(u'a'))) or isinstance(obj, numbers.Number) : 
            #string or mono-thing
            df = pd.DataFrame([obj,], columns = ["c0"])

        if not isinstance(df, pd.DataFrame) :
            raise Exception("%s is no Dataframe/Tuple/List/Dictionary" % name)

        for col in df:
            if df[col].dtype == np.int64:
                df[col] = df[col].astype(float)

        return df


    def _extract_table_names(self, q, env):
        """
        extracts table names from a sql query whose :
            - name if postfixed by $$,
            - name is found in given 'env' environnement
        example :
             - python variable is x=['a','b']
             - "select * from x$$" may return ['a', 'b']
        """
        tables = set()
        q_out = ""
        for query in (q+" -- ").split("$$"):
            table_candidate = query.split(' ')[-1] 
            if table_candidate in env:
               tables.add(table_candidate)
               q_out += query
            else:
                q_out += query+"$$"
        self.tmp_tables = list(set(tables))
        return self.tmp_tables , q_out[:-6]


    def _write_table(self, tablename, df, conn):
        "writes a dataframe to the sqlite database"
        for col in df.columns:
            if re.search("[()]", col):
                msg = "please follow SQLite column naming conventions: "
                msg += "http://www.sqlite.org/lang_keywords.html"
                raise Exception(msg)
        if self.do_log:
            self.log.append("(pandas) create table  %s  ..." % tablename)  
            cards = ','.join(['?'] * len(df.columns))
            self.log.append("(pandas) INSERT INTO  %s  VALUES (%s)"
                 % (tablename , cards))        
        # pandas 0.19 doesn't want it anymore
        if LooseVersion(pd.__version__) < LooseVersion("0.18.9"):
            to_sql(df, name = tablename, con = self.conn,  flavor = self.engine)
        else:
            to_sql(df, name = tablename, con = self.conn)

    def createpydef(self, sql):
        """generates and register a pydef instruction"""
        instruction = sql.strip('; \t\n\r')
        # create Python function in Python
        print("***",instruction[2:],"***")
        exec(instruction[2:], globals(), locals())
        # add Python function in SQLite
        firstline = (instruction[5:].splitlines()[0]).lstrip()
        firstline = firstline.replace(" ", "") + "("
        instr_name = firstline.split("(", 1)[0].strip()
        instr_parms = firstline.count(',')+1
        instr_add = (("self.conn.create_function('%s', %s, %s)" % (
                      instr_name, instr_parms, instr_name)))
        exec(instr_add, globals(), locals())
        # housekeeping definition of pydef in a dictionnary
        the_help = dict(globals(), **locals())[instr_name].__doc__
        self.conn_def[instr_name] = {
            'parameters': instr_parms, 'inst': instr_add,
            'help': the_help, 'pydef': instruction}
        return instr_name
    
    def cursor(self, q, env):
        """
        query python or sql datas, returns a cursor of last instruction
        q: sql instructions, with 
            $x refering to a variable 'x' defined in the dictionnary
            x$$ refering to a table created with the variable 'x'   
        env: dictionnary of variables available to the sql instructions
             either manual : {'users':users,'limit':limit}
             otherwise the default suggested is : dict(globals(),**locals())  
        """

        #initial cleanup 
        self.remove_tmp_tables # remove temp objects created for previous sql
        sql = "".join(self.get_sqlsplit(q, remove_comments=True)) # no comments
        
        #importation of needed Python tables into SQL
        names_env = {} #ensure we use a dictionnary
        if isinstance(env, dict):
            names_env = env
        elif isinstance(env, (list,tuple)) and len(env)>0 and isinstance(env[-1], dict):
            names_env = env[-1]
        tables, sql = self._extract_table_names(sql, names_env)
        for table_ref in tables:
            table_sql = table_ref+"" # drop the "$$"
            df = names_env[table_ref]
            df = self._ensure_data_frame(df, table_ref)
            #destroy previous Python temp table before importing the new one
            pre_q = "DROP TABLE IF EXISTS %s" % table_sql.join(self.delimiters)
            cur = self._execute_sql (pre_q)
            self._write_table( table_sql, df, self.conn)
        #multiple sql must be executed one by one
        for q_single in self.get_sqlsplit(sql, remove_comments=True) :
            # inserting pydef from sqlite_bro
            instru = q_single.replace(";", "").strip(' \t\n\r')
            # for the show: first_line = (instru + "\n").splitlines()[0]
            if instru[:5] == "pydef":
                pydef = self.createpydef(instru)
                cur=self._execute_cte("",  env)  # avoid a bad message
            elif (instru[:8]).upper() == "PERSIST ":  # upload à la IPYTHON-SQL
                shell_list = shlex.split(instru.replace(',',' '))  # magic standard library
                for table_ref in shell_list[1:]:
                    #destroy previous Python temp table before importing the new one
                    pre_q = "DROP TABLE IF EXISTS %s" % table_ref.join(self.delimiters)
                    cur = self._execute_sql (pre_q)
                    df = names_env[table_ref]
                    df = self._ensure_data_frame(df, table_ref)
                    self._write_table( table_ref, df, self.conn)
            elif instru[:1] == ".":  # a shell command !
                # handle a ".function" here !
                table_ref = shlex.split(instru)  # magic standard library
            elif q_single.strip() != "":
                cur = self._execute_cte(q_single,  env)
        return cur

    def rows(self, q, env):
        "same as .cursor , but returns a list of rows (a list of tuples)"
        result = self.cursor( q, env).fetchall()
        self.remove_tmp_tables()
        return result

    def column(self, q, env, column=0):
        "same as rows , but returns a simple list of the Nth column values"
        result = [x[column] for x in self.cursor( q, env).fetchall()]
        self.remove_tmp_tables()
        return result

    def df(self, q, env):
        "same as .cursor , but returns a pandas dataframe"
        cur = self.cursor( q, env)
        result = None
        rows = cur.fetchall()
        if not isinstance(rows, list):
            rows = list(rows)
        if cur.description is not None: 
            columns = [col_desc[0] for col_desc in cur.description]
            result = pd.DataFrame(rows, columns=columns)
        self.remove_tmp_tables()
        return result

   
if __name__ == '__main__':
        #create the object and 'comfort' shorcuts
        bsql = baresql() # Create an Sqlite Instance in memory

        bsqldf = lambda q: bsql.df(q, dict(globals(),**locals()))
        bsqlrows = lambda q: bsql.rows(q, dict(globals(),**locals()))
        bsqlcolumn = lambda q: bsql.column(q, dict(globals(),**locals()))

        ##basic example 
        #user = [(i, "user N°"+str(i)) for i in range(5)]
        #limit = 2 
        #sql = "select * from user$$ where c0 <= $limit"
        #print (bsqldf(sql)) 

        ##multiple-sql example
        #sql = '''drop table if exists winner;
        #       create table winner as select * from user$$ where c0 > $limit ;
        #       select * from winner'''
        #print (bsqlrows(sql) )

        ## Common Table Expression (in SQLite) example
        ## Let's find the Primes numbers below 100  
        #bsql=baresql(keep_log = True ) #Trace how Sqlite is feeded
        #ints=[ i for i in range(2,100)]
        #sql="""with i as (select cast(c0 as INTEGER) as n from ints$$),
        #    non_primes as (select distinct i.n from i 
        #    inner join i as j on i.n>=j.n*j.n where round(i.n/j.n)*j.n = i.n )
        #    select * from i where n not in (select * from non_primes)
        #    """ 
        #print (bsqlcolumn(sql)) #show resut
        #print(";\n".join(bsql.log)) #show how it happened
        
