# -*- coding: utf-8 -*-
"""cte_to_sqlite module. Translate CTE sql into SQlite sql
usage on the commande line :
   python cte_to_sqlite -i inputfile [-o outputfile] [-v]
   inputfile  = sql file with CTE  
   outputfile = sql file with CTE instructions replaced
   -v = use temporary views instead of in-lining

usage as a function :
   cte_to_sqlite(sql, cte_inline = True, remove_comments = False)   
"""

def cte_to_sqlite(sql, cte_inline = True, remove_comments = False):
    "translate a CTE SQL string into a SQlite SQL string"

    import re
    def get_token( sql, start = 0):
        "for given sql start position, give token type and next token start"
        length = len(sql) ; 
        i = start ; token = 'TK_OTHER'
        dico = {' ':'TK_SP', '\t':'TK_SP', '\n':'TK_SP', '\f':'TK_SP',
         '\r':'TK_SP', '(':'TK_LP', ')':'TK_RP', ';':'TK_SEMI', ',':'TK_COMMA',
         '/':'TK_OTHER', "'":'TK_STRING',"-":'TK_OTHER', 
         '"':'TK_STRING', "`":'TK_STRING'}
        if length > start:
            if sql[i] == "-" and i < length and sql[i:i+2] == "--" :
                #this Token is an end-of-line comment : --blabla
                token='TK_COM'
                i = sql.find("\n", start)  
                if i <= 0: i = length  
            elif sql[i] == "/" and i < length and sql[i:i+2] == "/*":
                #this Token is a comment block : /* and bla bla \n bla */
                token='TK_COM'
                i = sql.find("*/",start)+2  
                if i <= 1:  i = length
            elif sql[i] not in dico : 
                #this token is a distinct word (tagged as 'TK_OTHER') 
                while i < length and sql[i] not in dico: i += 1
                #For Trigger creation, we need to detect BEGIN END 
                if  sql[start:i].upper()=='BEGIN' : token = 'TK_BEG'
                elif sql[start:i].upper()=='END' : token = 'TK_END'
            else:
                #default token analyze case
                token = dico[sql[i]]
                if token == 'TK_SP':  
                    #Find the end of the 'Spaces' Token just detected  
                    while (i < length and sql[i] in dico and 
                      dico[sql[i]] == 'TK_SP'):  i += 1
                elif token == 'TK_STRING':  
                    #Find the end of the 'String' Token just detected  
                    delimiter = sql[i]
                    if delimiter != "'": token = 'TK_ID' #usefull nuance ?
                    while (i < length  ):
                        i = sql.find(delimiter , i+1)
                        if i <= 0: # String is never closed
                            i = length
                            token = 'TK_ERROR'
                        elif i < length -1 and sql[i+1] == delimiter :
                            i += 1   # double '' case, so ignore and continue
                        else: 
                            i += 1
                            break #normal End of a  String 
                else: 
                    if i < length : i += 1
        return i, token


    def get_sqlsplit(sql, remove_comments=False):
        """split an sql file in list of separated sql orders"""
        beg = end = 0; length = len(sql) ; translvl = 0
        sqls = []
        while end < length-1:
            tk_end , token = self.get_token(sql,end)
            if token == 'TK_BEG' : translvl += 1
            elif token == 'TK_END' : translvl -= 1
            elif (token == 'TK_SEMI' and translvl==0) or tk_end == length: 
                # end of a single sql
                sqls.append(sql[beg:tk_end])
                beg = tk_end
            elif token == 'TK_COM' and remove_comments: # clear comments option
                sql = sql[:end]+' '+ sql[tk_end:]
                length = len(sql)
                tk_end = end + 1
            end = tk_end
        if beg < length :
               sqls.append(sql[beg:])
        return sqls
        
             
    def split_sql_cte(sql, cte_inline = True, remove_comments = False):
        """
        split a cte sql in several non-cte sqls
        feed cte_views + cte_tables list for post-execution clean-up
        if cte_inline = True, inline the CTE views instead of creating them
        """
        if remove_comments:
            sql="".join(get_sqlsplit(sql, remove_comments))
        beg = end = 0; length = len(sql)
        is_with = False
        status = "normal"
        sqls = []
        level = 0 ;from_lvl={0:False} ; last_other=""
        cte_dico = {} #dictionnary created from CTE definitions 
        while end < length:
            tk_end , token = get_token(sql,end)
            tk_value = sql[end:tk_end]
            if ((status == "normal" and level == 0 and token =="TK_OTHER" and
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
                            sqls.append("DROP TABLE IF EXISTS %s;\n" % v_name)
                            sqls.append("create temp table %s;\n" % v_full)
                            #insert the cte in that table
                            sqls.append("insert into  %s %s;\n" % (v_name
                                        ,  sql[cte_lp + 1:cte_rp]))
                        else:
                             if not cte_inline: #for "with X as (", create view
                                 sqls.append("DROP VIEW IF EXISTS %s;\n"
                                 % v_name)
                                 #add the cte as a view
                                 sqls.append("create temp view %s as %s;\n" % (
                                      v_name , sql[cte_lp + 1:cte_rp]))
                             else: #for "with X as (", create a dictionnary
                                 cte_dico[v_name]=sql[cte_lp + 1:cte_rp]

            elif token == "TK_OTHER" and cte_inline: 
                if tk_value.lower() == "from":
                    from_lvl[level] = True
                elif from_lvl[level]:
                    if last_other in(',', 'from', 'join') and (
                    tk_value in cte_dico):
                        #check if next token is as
                        bg , en , tknext = tk_end , tk_end , 'TK_SP'
                        while en < length and tknext == 'TK_SP' :
                            bg, (en , tknext) = en, get_token(sql , en)
                        #avoid the "as x as y" situation
                        if sql[bg:en].lower() != 'as': 
                            sql2 = (sql[:end ] + "("+ cte_dico[tk_value] + 
                              ") as " + tk_value + " ")
                        else:
                            sql2 = (sql[:end ] + "("+ cte_dico[tk_value] + 
                              ")  " + " ")
                        
                        tk_end , sql = len(sql2)   ,  sql2 + sql[tk_end:]
                        length = len(sql)                        

            if token == 'TK_SEMI' or tk_end == len(sql): #a non-cte sql
                sqls.append(sql[beg:tk_end])
                beg = tk_end
                level = 0
                status="normal"
                cte_dico = {}
            # continue while loop            
            end = tk_end
            if token != "TK_SP":
                last_other = tk_value.lower()
        return sqls

    return "".join(split_sql_cte(sql, cte_inline, remove_comments))
  
if __name__ == '__main__':
    import sys
    import getopt
    opts=[("z","z")]; demo = True ; cte_inline = True ; outfile = ""
    if sys.argv[0] !="-c": #avoid issues with under Ipython
        opts, args = getopt.getopt(sys.argv[1:], "i:o:v")
        # process options
    sql = """with x as (y)
, x1(z) as (select z from x)
select * from x1 where z not in x"""               
    demo = True ; cte_inline = True ; outfile = ""
    for o, a in opts:
        if o == "-v":
            cte_inline = False
        if o == "-i":
            demo = False
            with open (a, "r") as myfile:
                sql="".join(myfile.readlines())
        if o == "-o":
            outfile = a 
    if demo:
        print (__doc__)
        print("\n Examples :\n***original sql : ***\n", sql)
        print("\n**cte_to_sqlite(sql)**:\n" + cte_to_sqlite(sql))
        print("\n\n**cte_to_sqlite(sql , cte_inline = False) **:\n")
        print(cte_to_sqlite(sql, cte_inline = False))
    else:
        if outfile  != "":
            with open (outfile, "w") as myfile:
                myfile.write(cte_to_sqlite(sql, cte_inline))
        else:
            print(cte_to_sqlite(sql, cte_inline))
