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

    def __init__(self, connection="sqlite://", keep_log = False, 
                 cte_inline = True):
        """
        conn = connection string  
        example :
        "sqlite://" = sqlite in memory
        "sqlite:///.baresql.db" = sqlite on disk database ".baresql.db"
        cte_inline = inline CTE for SQLite instead of creating temporary views
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

        #SQLite CTE translation infrastructure
        self.cte_inline = cte_inline
        self.cte_views = []
        self.cte_tables = []
        self.cte_dico = {} #dictionnary created from CTE definitions 
        
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
                i = sql.find("\n", start) #TK_COM feeding
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
        sqls = []
        while end < length:
            tk_end , token = self.get_token(sql,end)
            if token == 'TK_SEMI' or tk_end == length: # end of a single sql
                sqls.append(sql[beg:tk_end])
                beg = tk_end
            if token == 'TK_COM' and remove_comments: # clear comments option
                sql = sql[:end]+' '+ sql[tk_end:] 
                length = len(sql)
            end = tk_end 
        return sqls
        
             
    def _execute_sql(self, q_in ,  env = None):
        "execute sql but intercept log"
        if self.do_log:
            self.log.append(q_in)
        return execute(q_in ,self.conn, params=env)


    def _split_sql_cte(self, sql, cte_inline = True):
        """
        split a cte sql in several non-cte sqls
        feed cte_views + cte_tables list for post-execution clean-up
        if cte_inline = True, inline the CTE views instead of creating them
        """
        beg = end = 0; length = len(sql)
        is_with = False
        status = "normal"
        sqls = []
        level = 0 ;from_lvl={0:False} ; last_other=""
        while end < length:
            tk_end , token = self.get_token(sql,end)
            tk_value = sql[end:tk_end]
            if token == 'TK_SEMI' or tk_end == length: #a non-cte sql
                sqls.append(sql[beg:tk_end]) 
                beg = tk_end
                level = 0
                status = "normal"
            elif ((status == "normal" and level == 0 and token =="TK_OTHER" and
            tk_value.lower() == "with") 
            or (token == 'TK_COMMA' and status == "cte_next")):
                status = "cte_start"; v_full=""
                is_with = True #cte_launcher
            elif status == "cte_next"  and token=="TK_OTHER":
                status = "normal"; beg = end
            elif status == "cte_start"  and token=="TK_OTHER":
                status = "cte_name"
                v_name = tk_value ; beg=end #new beginning of sql
            elif status == "cte_name"  and level == 0 and token=="TK_OTHER":
                if tk_value.lower() == "as": 
                    status = "cte_select"
                else:
                    cte_table = tk_value
            elif token=='TK_LP':
                    level += 1 ;from_lvl[level] = False
                    if level == 1 :
                        cte_lp = end #for later removal, if a cte expression
            elif token == 'TK_RP':
                level -= 1
                if level == 0:
                    if status == "cte_name":
                        v_full = sql[beg:tk_end]
                    elif status == "cte_select":
                        beg = cte_rp = end
                        status = "cte_next"
                        #end of a cte, let's transform the raw_sql
                        #get name of the cte view/table
                        if v_full != "":
                            #if "with X(...) as", we do create table +insert
                            sqls.append("DROP TABLE IF EXISTS %s " % v_name)
                            sqls.append("create temp table %s " % v_full)
                            #insert the cte in that table
                            sqls.append("insert into  %s %s" % (v_name
                                        ,  sql[cte_lp + 1:cte_rp]))
                            #mark the cte table for future deletion
                            self.cte_tables.insert (0 , v_name)
                        else:
                             if not cte_inline: #for "with X as (", create view
                                 sqls.append("DROP VIEW IF EXISTS %s" % v_name)
                                 #add the cte as a view
                                 sqls.append("create temp view %s as %s " % (
                                      v_name , sql[cte_lp + 1:cte_rp]))
                                 #mark the cte view for future deletion
                                 self.cte_views.insert (0 , v_name)
                             else: #for "with X as (", create a dictionnary
                                 self.cte_dico[v_name]=sql[cte_lp + 1:cte_rp]

            if token == 'TK_SEMI' or tk_end == len(sql):
                sqls.append(sql[beg:tk_end])
                beg = tk_end
                level = 0
                status="normal"
                self.cte_dico = {}
            elif token == "TK_OTHER" and cte_inline: 
                if tk_value.lower() == "from":
                    from_lvl[level] = True
                elif from_lvl[level]:
                    if last_other in(',', 'from', 'join') and (
                    tk_value in self.cte_dico):
                        #check if next token is as
                        bg , en , tknext = tk_end , tk_end , 'TK_SP'
                        while en < length and tknext == 'TK_SP' :
                            bg, (en , tknext) = en, self.get_token(sql , en)
                        #avoid the "as x as y" situation
                        if sql[bg:en].lower() != 'as': 
                            sql2 = (sql[:end ] + "("+ self.cte_dico[tk_value] + 
                              ") as " + tk_value + " ")
                        else:
                            sql2 = (sql[:end ] + "("+ self.cte_dico[tk_value] + 
                              ")  " + " ")
                        
                        tk_end , sql = len(sql2)   ,  sql2 + sql[tk_end:]
                        length = len(sql)                        
            # continue while loop            
            end = tk_end
            if token != "TK_SP":
                last_other = tk_value.lower()
        self.cte_dico = {}    
        return sqls


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
            q_final_list = self._split_sql_cte(sql, self.cte_inline) 
            #multiple sql must be executed one by one
            for q_single in q_final_list:
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
        q = "".join(self.get_sqlsplit(sql, True)) #remove comments from the sql 
        
        #importation of needed Python tables into SQl
        tables = self._extract_table_names(q, env)
        for table_ref in tables:
            table_sql = table_ref+"$$"
            df = env[table_ref]
            df = self._ensure_data_frame(df, table_ref)
            #destroy previous Python temp table before importing the new one
            pre_q = "DROP TABLE IF EXISTS [%s]" % table_sql
            cur = self._execute_sql (pre_q, env)
            self._write_table( table_sql, df, self.conn)
        #multiple sql must be executed one by one
        for q_single in self.get_sqlsplit(sql, True) :
            if q_single.strip() != "":
                #cleanup previous CTE temp tables before executing another sql
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
        #print(";\n".join(bsql.log)) #show how it happened
        
