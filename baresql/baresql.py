# -*- coding: utf-8 -*-
import re
import sqlite3 as sqlite
import numpy as np
import pandas as pd
from pandas.io.sql import write_frame, execute

class baresql(object):
    """
    baresql allows you to query in sql any of your python datas.
    
    in the sql :
    - '$s' refers to the variable 's' 
    - 'l$$' refers to the table created with the list/array/dictionnary 'l'
            columns of 'l$$' will be l$$.c0 ... l$$.cN (unless pre-defined)

    example :
        #create the object
        from baresql import baresql 
        bsql=baresql()

        user = [(i, "user N°"+str(i)) for i in range(7)]
        limit = 4 
        sql="select * from user$$ where c0 <= $limit"

        bsql.df(sql,locals()) 

    baresql re-use or re-implement parts of the code of 
       . github.com/yhat/pandasql (MIT licence, Copyright 2013 Yhat, Inc)
       . github.com/pydata/pandas (BSD simplified licence
       Copyright 2011-2012, Lambda Foundry, Inc. and PyData Development Team)
    """

    def __init__(self, connection="sqlite://", keep_log = False):
        """
        conn = connection string  
        example :
        "sqlite://" = sqlite in memory
        "sqlite:///.baresql.db" = sqlite on disk database ".baresql.db"
        """

        #identify sql engine and database
        self.connection = connection
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
        self.tmp_tables = []

        #logging infrastructure
        self.do_log = keep_log
        self.log = []

    def close(self):
        "proper closing"
        self.remove_tmp_tables
        self.conn.close

    def remove_tmp_tables(self):
        "remove temporarly created tables"
        for table_sql in self.tmp_tables:
            pre_q = "DROP TABLE IF EXISTS [%s]" % table_sql
            cur = self._execute_sql(pre_q )
        self.tmp_tables = []    

    def _splitcsv(self, csv_in, separator = ",", string_limit = "'"):
        "split a csv string respecting string delimiters"
        x = csv_in.split(string_limit)
        if len(x) == 1 :
            #Basic situation no string delimiter to worry about
            return csv_in.split(separator)
        else:
            #Identify and replace active separators : the ones not in a string 
            for i in range(0,len(x), 2):
               x[i] = x[i].replace(separator, "<µ²é£>")
            #Correct split is on this separator
            return string_limit.join(x).split("<µ²é£>")

    def _cleanup_sql(self, sql_in, separator = ",", string_limit = "'"):
        "remove --comments from the sql"
        q=["\n".join((x.split("\n")[1:])) for x in self._splitcsv(sql_in,"--")]
        return q
             
    def _execute_sql(self, q_in ,  env = None):
        "execute sql but intercept log"
        if self.do_log:
            self.log.append(q_in)
        return execute(q_in ,self.conn, params=env)

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

        if not isinstance(df, pd.DataFrame) :
            raise Exception("%s is no Dataframe/Tuple/List/Dictionary" % name)

        for col in df:
            if df[col].dtype == np.int64:
                df[col] = df[col].astype(np.float)

        return df

    def _extract_table_names(self, q, env):
        """
        extracts table names from a sql query whose :
            - name if postfixed by $$,
            - name is found in given 'env' environnement
        example : "select * from a$$, b$$, a$$" may return ['a', 'b']
        """

        tables = set()
        next_is_table = False
        for query in q.split("$$"):
            table_candidate = query.split(' ')[-1] 
            if table_candidate in env:
               tables.add(table_candidate)
        self.tmp_tables = list(set(tables))
        return self.tmp_tables


    def _write_table(self, tablename, df, conn):
        "writes a dataframe to the sqlite database"
    
        for col in df.columns:
            if re.search("[() ]", col):
                msg = "please follow SQLite column naming conventions: "
                msg += "http://www.sqlite.org/lang_keywords.html"
                raise Exception(msg)
        write_frame(df, name = tablename, con = self.conn, flavor = 'sqlite')


    def cursor(self, q, env):
        """
        query python or sql datas, returns a cursor of last instruction
        q: sql instructions, with 
            $x refering to a variable 'x' defined in the dictionnary
            x$$ refering to a table created with the variable 'x'   
        env: dictionnary of variables available to the sql instructions
             locals() and globals() are your python local/global variables
             dict(globals(),**locals()) is the default python view of variables
        """

        #initial cleanup (if we couldn't do it before)
        self.remove_tmp_tables

        tables = self._extract_table_names(q, env)
        for table_ref in tables:
            table_sql = table_ref+"$$"
            df = env[table_ref]
            df = self._ensure_data_frame(df, table_ref)
            #pre_destroy temporary table
            pre_q = "DROP TABLE IF EXISTS [%s]" % table_sql
            cur = self._execute_sql (pre_q, env)
            self._write_table( table_sql, df, self.conn)
        #multiple sql must be separated per a ';'
        for q_single in self._splitcsv(q,';') :
            if q_single.strip() != "":
                cur = self._execute_sql(q_single,  env)
        return cur

    def rows(self, q, env):
        "same as .cursor , but returns a list of rows"
        result = self.cursor( q, env).fetchall()
        self.remove_tmp_tables
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
        self.remove_tmp_tables
        return result

   
if __name__ == '__main__':
        #create the object
        bsql = baresql() # in memory

        user = [(i, "user N°"+str(i)) for i in range(5)]
        limit = 2 
        sql = "select * from user$$ where c0 <= $limit"

        print (bsql.df(sql,locals())) 

        #more sophisticate
        bsqldf = lambda q: bsql.df(q,  dict(globals(),**locals()))
        
        sql = '''drop table if exists winner;
               create table winner as 
                   select c0 No, c1 Name from user$$ where c0 > $limit ;
               select * from winner'''
               
               
        print ( bsqldf(sql) )
        
