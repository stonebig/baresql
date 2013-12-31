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
        self.cte_views = []
        self.cte_tables = []

        #logging infrastructure
        self.do_log = keep_log
        self.log = []

    def close(self):
        "proper closing"
        self.remove_tmp_tables
        self.conn.close

    def remove_tmp_tables(self, origin="all"):
        "remove temporarly created tables"
        if origin in ("all", "tmp"):
            for table in self.tmp_tables:
                cur = self._execute_sql("DROP TABLE IF EXISTS [%s]" % table)
            self.tmp_tables = []
            
        if origin in("all", "cte"):
            for view in self.cte_views:
                cur = self._execute_sql("DROP VIEW IF EXISTS [%s]" % view)
            self.cte_views = []
            for table in self.cte_tables:
                cur = self._execute_sql("DROP table IF EXISTS [%s]" % table)
            self.cte_tables = []

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

    def get_token(self, sql, start = 0):
        "return next token type and ending+1 from given sql start position"
        length = len(sql)
        i = start
        token = 'TK_OTHER'
        dico = {' ':'TK_SP', '\t':'TK_SP', '\n':'TK_SP', '\f':'TK_SP', 
         '\r':'TK_SP', '(':'TK_LP', ')':'TK_RP', ';':'TK_SEMI', ',':'TK_COMMA', 
         '/':'TK_OTHER', "'":'TK_STRING',"-":'TK_OTHER'}
        if length >  start:
            if sql[i] == "-" and  i < length and sql[i:i+2] == "--" :
                #an end-of-line comment 
                token='TK_COM'
                i = sql.find("\n", start)+1 #TK_COM feeding
                if i <= 0:
                    i = length    
            elif sql[i] == "/" and  i < length and sql[i:i+2] == "/*":
                #a comment block 
                token='TK_COM'
                i = sql.find("*/",start)+2 #TK_COM feeding
                if i <= 1:
                    i = length   
            elif sql[i] not in dico : #TK_OTHER feeding
                while i < length and sql[i] not in dico:
                    i += 1 
            else:     
                token = dico[sql[i]]
                i += 1
                if token == 'TK_SP': #TK_SP feeding
                    while (i < length and sql[i] in dico and 
                    dico[sql[i]] == 'TK_SP'):
                        i+=1 
                if token == 'TK_STRING': #TK_STRING feeding
                    while (i < length and sql[i] == "'"):
                        i+=1 #other (don't bother, case)
        return i, token

    def get_sqlsplit(self, sql, remove_comments=False):
        "split an sql file in list of separated sql orders"
        beg = end = 0; length = len(sql)
        sqls=[]
        while end < length:
            res = self.get_token(sql,end)
            if res[1]=='TK_SEMI' or res[0] == length: # end of a single sql order
                sqls.append(sql[beg:res[0]])
                beg = res[0]
            if res[1]=='TK_COM' and remove_comments: # optionnal clear of comments
                sql = sql[:end]+' '+ sql[res[0]:] 
                length = len(sql)
            end = res[0] 
        return sqls
        
    def _cleanup_sql(self, sql, separator = ",", string_limit = "'"):
        "remove --comments then /*comments*/ from the sql"
        q = "".join(get_sqlsplit(sql,remove_comments = True))
        return q
             
    def _execute_sql(self, q_in ,  env = None):
        "execute sql but intercept log"
        if self.do_log:
            self.log.append(q_in)
        return execute(q_in ,self.conn, params=env)

    def _execute_cte(self, q_in,  env):
        """transform Common Table Expression SQL into acceptable SQLite SQLs
           with w    as (y) z => create w as y;z
           with w(x) as (y) z => create w(x);insert into w y;z
        """
        q_raw = q_in.strip()
        if  self.engine != "sqlite" or q_raw[:4].lower()!="with":  
            #normal execute
            return self._execute_sql(q_raw,env)
        else:
            #transform the CTE into SQlite acceptable sql instructions
            #create a fake separator "<µ£!" to split sql at each '(', ')', ','
            ctex = "<µ£!,".join(self._splitcsv(q_raw[4:], ",", "'"))
            ctex = "<µ£!(".join(self._splitcsv(ctex, "(", "'"))
            ctex = "<µ£!)".join(self._splitcsv(ctex, ")", "'"))
            #split the intial raw sql accordingly
            ctel = self._splitcsv(ctex,"<µ£!") 

            #initialization before starting analisys
            level = 0 # index of current nested level of parenthesis
            cte_deb = 0 #index of current CTE temporary table start 
            cte_opening=0 # index of last opening parenthesis at level 0
            cte_as = 0 # index of as in current CTE  if "with X(...) as" case 

            #decoding of the CTE part of the sql
            for i in range(len(ctel)):
                if ctel[i][0] == "(": #one more level of parenthesis
                    if level == 0:
                        cte_opening = i #for later removal
                    level += 1
                elif ctel[i][0] == ")": #one less level of parenthesis
                    level -= 1
                    if level == 0: #when we're back to zero level
                        #'as' case of "with X(...) as " 
                        if ((ctel[i]+" x").split()[1]).lower() == "as":
                            cte_as = i
                        else:
                            #end of a cte, let's transform the raw_sql
                            #get name of the cte view/table
                            tmp_t = ctel[cte_deb].split()[0]
                            if cte_as > 0:
                               #if "with X(...) as", we do create table +insert
                               ctel[cte_deb] = ("DROP TABLE IF EXISTS [%s];" % 
                                 tmp_t + "create temp table " + ctel[cte_deb])
                               #replace the ' as '
                               ctel[cte_as] = ");\ninsert into [%s] " % tmp_t 
                               #mark the cte table for future deletion
                               self.cte_tables.insert (0 , tmp_t)
                            else:
                               #if "with X as (", we do create view
                               ctel[cte_deb] = ("DROP VIEW IF EXISTS [%s];" % 
                                 tmp_t + "create temp view " + ctel[cte_deb])
                               #mark the cte view for future deletion
                               self.cte_views.insert (0 , tmp_t)

                            #remove opening & closing bracket of CTE definition
                            ctel[cte_opening] = ctel[cte_opening][1:]
                            ctel[i]=";"+ctel[i][1:]
                            
                            #check if next part of the raw_sql is another cte
                            if ctel[i].strip() == ";" and ctel[i+1][0] == ",":
                                #it is : set start ot this next cte table
                                ctel[i+1] = ctel[i+1][1:]  
                                cte_opening = cte_deb = i+1 
                                cte_as = 0
                            else:
                                #it is not : end of CTE, stop transformations
                                break
            q_final = " ".join(ctel)                
            #CTE decoding has created multiple sql separated per a ';'
            for q_single in self._splitcsv(q_final,';') :
                if q_single.strip() != "":
                    cur = self._execute_sql(q_single,env)
            return cur


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
        if self.do_log:
            self.log.append("(pandas) create table [%s] ..." % tablename)  
            cards = ','.join(['?'] * len(df.columns))
            self.log.append("(pandas) INSERT INTO [%s] VALUES (%s)"
                 % (tablename , cards))        
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

        #initial cleanup 
        self.remove_tmp_tables # remove temp objects created for previous sql
        q = self._cleanup_sql(q) #remove annoying comments from the next sql
        
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
                #intermediate cleanup of previous cte tables, if there were
                self.remove_tmp_tables("cte")
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
        #print("\n".join(bsql.log)) #show how it happened
        
