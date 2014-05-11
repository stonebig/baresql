#!/usr/bin/python
# -*- coding: utf-8 -*-
import sqlite3 as sqlite 
import sys, os, locale
import csv

from tkinter import *
from tkinter import font
from tkinter import ttk
from tkinter.ttk import *
from tkinter import filedialog
from tkinter import messagebox

global database_file
global conn 
global conn_inst

#********* start of tkk part ***********
    
def sortby(tree, col, descending):
    """Sort a ttk treeview contents when a column is clicked on."""
    # grab values to sort
    data = [(tree.set(child, col), child) for child in tree.get_children('')]

    # reorder data
    data.sort(reverse=descending)
    for indx, item in enumerate(data):
        tree.move(item[1], '', indx)

    # switch the heading so that it will sort in the opposite direction
    tree.heading(col,
        command=lambda col=col: sortby(tree, col, int(not descending)))
    
class notebook_for_queries():
    """Create a Notebook with a list in the First frame
       and query results in following treeview frames """
    def __init__(self, root, queries):
        self.root = root
        self.notebook = Notebook(root) #ttk.
        
        self.fw_tabs = {} # tab_tk_id -> python tab object
        self.fw_labels = {} # tab_tk_id -> Scripting frame python object
        self.fw_results = {} # tab_tk_id ->   Results objects
        self.fw_result_nbs = {} # tab_tk_id -> Notebook of Results
        self.fw_result_nbs = {} # tab_tk_id -> Notebook of Results
        
        # Resize rules
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        #grid widgets
        self.notebook.grid(row=0, column=0, sticky=(N,W,S,E))

    def new_query_tab(self, title, query ):
        "add a new Tab 'title' to the notebook, containing the Script 'query'"

        fw_welcome = ttk.Panedwindow(tk_win, orient=VERTICAL)      
        fw_welcome.pack(fill = 'both', expand=True)
        self.notebook.add(fw_welcome, text=(title))

        #new "editable" script 
        f1 = ttk.Labelframe(fw_welcome, text='Script', width=200, height=100)
        fw_welcome.add(f1)
        fw_label = ttk.tkinter.Text(f1 ,bd =1)
        
        
        scroll = ttk.Scrollbar(f1,   command = fw_label.yview)
        fw_label.configure(yscrollcommand = scroll.set)
        fw_label.insert(END, (query))
        fw_label.pack(side =LEFT, expand =YES, fill =BOTH, padx =2, pady =2)
        scroll.pack(side =RIGHT, expand =NO, fill =BOTH, padx =2, pady =2)
 
        #keep tab reference  by tk id 
        working_tab_id = "." + fw_welcome._name
        #keep tab reference to tab (by tk id)
        self.fw_tabs[working_tab_id]  = fw_welcome        
        #keep tab reference to script (by tk id)
        self.fw_labels[working_tab_id]  = fw_label        
        #keep   reference to result objects (by tk id)
        self.fw_results[working_tab_id]  = []        

        #new "Results" Container 
        fr = ttk.Labelframe(fw_welcome, text='Results', width=200, height=100)
        fw_welcome.add(fr)
        
        #containing a notebook
        fw_result_nb = Notebook(fr) 
        fw_result_nb.pack(fill = 'both', expand=True)
        # Resize rules
        fw_welcome.columnconfigure(0, weight=1)
        #keep reference to result_nb objects (by tk id)
        self.fw_result_nbs[working_tab_id]  = fw_result_nb        
        
        #activate this tab print(self.notebook.tabs())
        self.notebook.select(working_tab_id) 
        #workaround to have a visible result pane on initial launch
        self.add_treeview(working_tab_id, "_", 
        "","click on ('->') to run Script")
        return working_tab_id #gives back tk_id reference of the new tab

    def remove_treeviews(self, given_tk_id  ):
        "remove results from given tab tk_id"
        for xx in self.fw_results[given_tk_id]:
            xx.grid_forget()
            xx.destroy()
        self.fw_results[given_tk_id]=[]    
        
    def add_treeview(self, given_tk_id,  columns, data, title = "__", subt=""):
        "add a dataset result to the given tab tk_id"
        #Get back reference to Notebooks tabs
        fw_welcome = self.fw_tabs[given_tk_id]
        fw_result_nb  =  self.fw_result_nbs[given_tk_id]           

        #Create a Labelframe to contain new resultset and scrollbars 
        f2 = ttk.Labelframe(fw_result_nb, 
            text=('(%s lines) %s' % (len(data),subt)), width=200, height=100) 
        f2.pack(fill = 'both', expand=True)
        fw_result_nb.add(f2 , text = title)

        #keep   reference to result objects (by tk id)
        working_tab_id = "." + fw_welcome._name
        self.fw_results[working_tab_id].append(f2)       
        #Create a Treeview to show the query result
        tree_columns = columns
        if type(tree_columns)==type('ee'):
            tree_columns=[tree_columns]
        if type(data)==type('ee'):
            data=[data]
        #data=queries
        fw_Box = Treeview(f2, columns=tree_columns, show="headings",
                          padding=(2, 2, 2,2))
        fw_vsb = Scrollbar(f2, orient="vertical", command=fw_Box.yview)
        fw_hsb = Scrollbar(f2, orient="horizontal", command=fw_Box.xview)
        fw_Box.configure(yscrollcommand=fw_vsb.set, xscrollcommand=fw_hsb.set)
        fw_Box.grid(column=0, row=0, sticky='nsew', in_=f2)
        fw_vsb.grid(column=1, row=0, sticky='ns', in_=f2)
        fw_hsb.grid(column=0, row=2, sticky='ew', in_=f2)

        #This new Treeview  may occupy all variable space
        f2.grid_columnconfigure(0, weight=1)
        f2.grid_rowconfigure(0, weight=1) 

        #feed Treeview Header
        for col in tuple(tree_columns):
            fw_Box.heading(col, text=col.title(),
                command=lambda c=col: sortby(fw_Box, c, 0))
            fw_Box.column(col, width=font.Font().measure(col.title()))

        #feed Treeview Lines
        for items in data:
            item=items
            if type(item)==type('ee'): # if line is a string, redo a tuple
                item=(items,)
            #replace line_return by space (grid don't like line_returns)            
            clean = lambda x: x.replace("\n"," ") if type(x)==type('ee') else x
            line_cells=tuple(clean(item[c]) for c  in range(len(tree_columns)))            
            #insert the line of data
            fw_Box.insert('', 'end', values=line_cells)
            # adjust columns length if necessary and possible
            for indx, val in enumerate(line_cells):
                try :
                    ilen = font.Font().measure(val)
                    if fw_Box.column(tree_columns[indx], width=None
                        ) < ilen and ilen<400 :
                        fw_Box.column(tree_columns[indx], width=ilen)
                except:
                    pass
         

#********* end of tkk part ***********



#tree objet subfunctions
def add_things(root_id , what , attached_db = ""):
    "fill a database structure tree on demand"
    global conn
    global conn_inst
    #Build list (objet_name, objet_text, creation_request) for 'what' category 
    if what=='master_table':
        sql= "SELECT 'sqlite_master', 'sqlite_master', '--(auto_created)'"
    elif what=='attached_databases':
        sql="PRAGMA database_list" 
    else:
        sql = ("""SELECT  name as keytree, name, sql FROM %ssqlite_master 
            WHERE type='%s' order by name;""" % (  attached_db, what))

    if what !="pydef":
        tables = conn.execute( sql ).fetchall()
    else : #pydef specific case
        tables=[]
        try :
            z = conn_inst[conn] 
        except:       
            z = conn_inst[conn] = {}
        xdef=[i for i in z.keys()]
        if len(xdef)>0:
            idt = db_tree.insert(root_id,"end", "%s%s" % (attached_db, what)
                   , text="%s (%s)" % (what, len(xdef)), values=("","") )   
            for inst in xdef:
                idet=conn_inst[conn][inst]
                db_tree.insert(idt,"end",("pydef %s%s" % (attached_db,inst )),
                    text="%s" %(inst),
                    tags=('run',), values=(idet["pydef"],""))
    #if  'attached_database' category, remove the first (main) database 
    if what=='attached_databases':
        tables = tables[1:]
        
    #level 1 : create  the "what" node (as not empty)
    if len(tables)>0:
        idt = db_tree.insert(root_id,"end", "%s%s" % (attached_db, what)
                             , text="%s (%s)" % (  what, len(tables)) 
                             , values=(conn,"") )
    #level 2 : create the 'founds' below  the 'what' node just created
    for tab in tables:
        definition = tab[2]
        #Get Table or View fields list , prepare 'detailed query' sql3
        sql2 = "SELECT * FROM  %s[%s] limit 0;" % (attached_db,tab[1])
        try :
            cursor = conn.execute(sql2 )
            columns = [col_desc[0] for col_desc in cursor.description]
            cursor.close
            #column by column select preparation
            sel_cols = "select ["+"] , [".join(columns)+"] from "
            sql3 = sel_cols + ("%s[%s] limit 999"% (attached_db,tab[1]))
        except :
            columns = [] ;sql3 = ""
        
        #include the description of it , specific for database_list
        if sql  == "PRAGMA database_list":
            definition = "ATTACH DATABASE '%s' as '%s'"%(tab[2],tab[1])
        idc = db_tree.insert(idt,"end",
                             "%s%s" % (attached_db,tab[0]) 
                             ,text=tab[1] ,values=(definition,sql3))

        db_tree.insert(idc,"end",("%s%s.%s" % (attached_db,tab[1], -1)),
                 text = ['(Definition)'],tags=('run',), values=(definition,""))
        #level 3 : create the detail (columns) for each 'founds'
        for c in range(len(columns)):
            db_tree.insert(idc,"end",("%s%s.%s" % (attached_db,tab[1], c)),
                 text=columns[c],tags=('run',),
                 values=(sql3,sql3))

    return [i[1] for i in tables]
    
def new_db():
    """create a new database"""
    global database_file
    global conn
    import sqlite3 as sqlite 
    filename_tk = filedialog.asksaveasfile(mode='w',defaultextension='.db',
              title="Define a new database name and location",                          
              filetypes=[("default","*.db"),("other","*.db*"),("all","*.*")])
    filename = filename_tk.name
    filename_tk.close
    if filename != "(none)":
        database_file =  filename 
        conn = sqlite.connect(database_file,
                   detect_types = sqlite.PARSE_DECLTYPES)
        actualize_db()
        
def new_db_mem():
   """connect to a memory database """  
   global database_file
   global conn
   database_file = ":memory:"
   conn = sqlite.connect(":memory:",
                   detect_types = sqlite.PARSE_DECLTYPES)
   actualize_db()
                
def open_db():
   """open an existing database"""
   global database_file
   global conn
   import sqlite3 as sqlite 
   filename = filedialog.askopenfilename(defaultextension='.db',
              filetypes=[("default","*.db"),("other","*.db*"),("all","*.*")])

   if   filename != "(none)":
       database_file =  filename 
       conn = sqlite.connect(database_file,
                   detect_types = sqlite.PARSE_DECLTYPES)
       actualize_db()
def close_db():
   """close database"""
   global conn
   global database_file
   try :
       db_tree.delete("Database")
   except :
       pass
   conn.close
   
def run_tab():
   """clear previous results and run current script of a tab"""
   nb = n.notebook
   active_tab_id = nb.select()
   
   #remove previous results
   n.remove_treeviews(active_tab_id)
   #get current selection (or all)
   fw =n.fw_labels[active_tab_id]
   script = ""
   try :
       script = (fw.get('sel.first', 'sel.last')) 
   except:
       script = fw.get(1.0,END)[:-1]   

   create_and_add_results(script, active_tab_id)
   #workaround bug http://bugs.python.org/issue17511 (for python <=3.3.2)
   #otherwise the focus is still set but not shown
   fw.focus_set()

def create_and_add_results(instructions, tab_tk_id):
    """execute instructions and add them to given tab results"""
    jouer = baresql()
    a_jouer = jouer.get_sqlsplit(instructions, remove_comments = True) 
    for instruction in a_jouer:
        instruction = instruction.replace(";","").strip(' \t\n\r')
        rows=[] ; first_line = instruction.splitlines()[0]
        rowtitles=("#N/A",); Tab_Title = "Qry"
        if instruction == "":
            #do nothing
            do_nothing = True
        
        elif instruction[:5] == "pydef" :
            instruction = instruction.strip('; \t\n\r')
            Tab_Title = "Info"
            exec(instruction[2:]  , globals() , locals())
            firstline=(instruction[5:].splitlines()[0]).lstrip()
            firstline = firstline.replace(" ","") + "(" 
            instr_name=firstline.split("(",1)[0].strip()
            instr_parms=firstline.count(',')+1
            instr_add = "conn.create_function('%s', %s, %s)" %(
               instr_name,instr_parms, instr_name)

            exec(instr_add , globals() , locals())
            rowtitles=("Creating embedded python function",)
            for i in (instruction[2:].splitlines()) :
               rows.append((i,))             
            rows.append((instr_add,))

            #manual housekeeping
            global conn_inst
            try :
                conn_def = conn_inst[conn]
            except:
                conn_inst[conn] = {}
                conn_def = conn_inst[conn]
            try:    
                 the_help= dict(globals(),**locals())[instr_name].__doc__
                 conn_def[instr_name]={'parameters':instr_parms,
                                       'help':the_help, 'pydef':instruction}
            except:
                pass
        else:
          try :
              cur = conn.execute(instruction)
              my_curdescription=cur.description
              rows = cur.fetchall()
              #A query may have no result( like for an "update")
              if    cur.description != None :
                  rowtitles = [row_info[0] for row_info in cur.description]
              cur.close
          except sqlite.Error as msg:#OperationalError
              rowtitles=('Error !',)
              rows=[(msg,)]
              n.add_treeview(tab_tk_id, rowtitles, rows,"Error !", first_line )
              break
        #end of one sql
        if rowtitles != ("#N/A",) :#rows!=[]  :
              n.add_treeview(tab_tk_id, rowtitles, rows, Tab_Title, first_line)

def del_tabresult():
   """delete active notebook tab's results"""
   #get active notebook tab
   nb = n.notebook  
   active_tab_id = nb.select()
   
   #remove active tab's results
   n.remove_treeviews(active_tab_id)

def del_tab():
   """delete active notebook tab's results"""
   #get active notebook tab
   nb = n.notebook
   active_tab_id = nb.select()

   #remove active tab from notebook
   nb.forget(nb.select() )


def new_tab():
   """delete active notebook tab's results"""
   #get active notebook tab
   n.new_query_tab("___","")

def attach_db():
   """attach an existing database"""
   global database_file
   global conn
   import sqlite3 as sqlite 
   filename = filedialog.askopenfilename(defaultextension='.db',
              title="Choose a database to attach ",    
              filetypes=[("default","*.db"),("other","*.db*"),("all","*.*")])
   attach = ((filename.replace("\\","/")).split("/")[-1]).split(".")[0]

   if   filename != "(none)":
       attach_order = "ATTACH DATABASE '%s' as '%s' "%(filename,attach);
       cur = conn.execute(attach_order)
       cur.close
       actualize_db()

def import_csvtb_ok(thetop, entries):
    "read input values from tk formular"
    #file, table, separator, header, create, replace_data   

    csv_file = entries[0][1]().strip()
    table_name = entries[1][1]().strip()
    separ = entries[2][1]()
    header = entries[3][1]()
    creation = entries[4][1]()
    replacing = entries[5][1]()
    encoding_is = entries[6][1]()
 
    if   csv_file != "(none)" and len(csv_file)*len(table_name)*len(separ)>1:
       thetop.destroy()
       curs = conn.cursor()
       reader = csv.reader(open(csv_file, 'r', encoding = encoding_is),
                           delimiter = separ, quotechar='"')
       #read first_line for headers and/or number of columns
       row = next(reader) 
       sql="INSERT INTO %s  VALUES(%s);" % (
               table_name,  ",".join(["?"]*len(row)))
       if creation:
              curs.execute("drop TABLE if exists [%s];" % table_name)
              if header:
                  def_head=",".join([('[%s]' % i) for i in  row])
                  curs.execute("CREATE TABLE [%s] (%s);"
                      % (table_name, def_head))
              else:
                  def_head=["c_"+("000" +str(i))[-3:] for i in range(len(row))]
                  def_head=",".join(def_head)
                  curs.execute("CREATE TABLE [%s] (%s);"
                      % (table_name, def_head))
       if replacing:
              curs.execute("delete from [%s];" % table_name)
              replacing = False
       if not header:
              curs.execute(sql, row)
       curs.executemany(sql, reader)
       conn.commit()
       actualize_db()
 
def create_dialog(title, fields, buttons , datas):
    "create a formular with title, fields, button, data"
    #Drawing the request form 
    top = Toplevel()
    top.title(title)

    content = ttk.Frame(top)
    frame = ttk.LabelFrame(content, borderwidth = 5,  text = datas[0]
     ,relief="sunken", width = 200, height = 100)

    content.grid(column = 0, row = 0, sticky = (N, S, E, W))
   
    frame.grid(column = 2 , row = 0 , columnspan = 1 , 
              rowspan = len(fields)+1 , sticky = (N, S, E, W) )

    #text of file
    fw_label = ttk.tkinter.Text(frame ,bd =1)
    fw_label.pack(side =LEFT, expand =YES, fill =BOTH)     
    scroll = ttk.Scrollbar(frame,   command = fw_label.yview)
    scroll.pack(side =RIGHT, fill =Y)
    fw_label.configure(yscrollcommand = scroll.set)
    fw_label.insert(END, datas[1])
   
    #typ-it choices
    entries = []
    for field in fields:
        ta_col = len(entries)
        if field[1]==True or field[1]==False:
            name_var = BooleanVar()
            name = ttk.Checkbutton(content, text=field[0], 
                                 variable = name_var, onvalue=True)
            name_var.set(field[1])  
            name.grid(column=1, row=ta_col,   sticky=(N, W), pady=5, padx=5)
            entries.append((field[0], name_var.get))
        else :
            namelbl = ttk.Label(content,   text=field[0] )
            namelbl.grid(column=0, row=ta_col, sticky=(N, E), pady=5, padx=5)
            name_var = StringVar()
            name = ttk.Entry(content, textvariable = name_var)
            name_var.set(field[1])
            name.grid(column=1, row=ta_col,   sticky=(N, E, W), pady=5, padx=5)
            entries.append((field[0], name_var.get))
    #add Text
    entries.append(('data', lambda : fw_label.get('0.0',END)))
    okbutton = ttk.Button(content, text = buttons[0], 
            command = lambda  a = top, b = entries: (buttons[1])(a, b)) 
    cancelbutton = ttk.Button(content, text = "Cancel", command = top.destroy)

    okbutton.grid(column=0, row=len(entries))
    cancelbutton.grid(column=1, row=len(entries))
    for x in range(3):
        Grid.columnconfigure(content, x,weight=1)
    for y in range(3):
        Grid.rowconfigure( content, y, weight=1)
   
    # Resize rules
    top.columnconfigure(0, weight=1)
    top.rowconfigure(0, weight=1)
    #grid widgets
    content.grid( column=0, row=0,sticky=(N,W,S,E))
    top.grab_set()
      
def import_csvtb():
    """import csv dialog (with guessing of encoding and separator)"""
    import locale
    csv_file = filedialog.askopenfilename(defaultextension='.db',
              title="Choose a csv file (with header) to import ",
              filetypes=[("default","*.csv"),("other","*.txt"),("all","*.*")])

    #Guess encoding
    with open(csv_file, "rb") as f:
        data = f.read(5)
    if data.startswith(b"\xEF\xBB\xBF"): # UTF-8 "BOM"
        encodings = ["utf-8-sig"]
    elif data.startswith(b"\xFF\xFE") or data.startswith(b"\xFE\xFF"): # UTF-16
        encodings = ["utf-16"]
    else: #in Windows, guessing utf-8 doesn't work, so we have to try
        try:
            with open(csv_file, encoding = "utf-8") as f:
                preview = f.read(222222)  
                encodings = ["utf-8"]
        except:
            encodings = [locale.getdefaultlocale()[1], "utf-8"]

    #Guess Header and delimiter
    with open(csv_file, encoding = encodings[0]) as f:
        preview = f.read(9999)  
    try:
        dialect = csv.Sniffer().sniff(preview)
        has_header = csv.Sniffer().has_header(preview)
        default_sep = dialect.delimiter
    except: #sniffer can fail
        has_header = True ; default_sep=","    

    #Request form (see http://www.python-course.eu/tkinter_entry_widgets.php)
    fields = [('csv Name', csv_file )
     ,('table Name', (csv_file.replace("\\","/")).split("/")[-1].split(".")[0])
     ,('column separator', default_sep)
     ,('Header line', has_header)
     ,('Create table', True)
     ,('Replace existing data', True)
     ,('Encoding', encodings[0]) ] 
 
    create_dialog(("Importing %s" % csv_file ), fields  
                  , ("Import",  import_csvtb_ok)                  
                  , ("first 3 lines " , "\n\n".join(preview.splitlines()[:3])))


def export_csv_ok(thetop, entries):
    "export a csv table (action)"
    import sqlite3
    global conn
    import csv
    csv_file    = entries[0][1]().strip()
    separ       = entries[1][1]()
    header      = entries[2][1]()
    encoding_is = entries[3][1]()
    query_is     = entries[-1][1]() 
    cursor = conn.cursor()
    cursor.execute(query_is)
    thetop.destroy()
    with open(csv_file, 'w', newline='', encoding = encoding_is) as fout:
        writer = csv.writer(fout, delimiter=',',
                            quotechar='"', quoting=csv.QUOTE_MINIMAL)
        if header:
            writer.writerow([i[0] for i in cursor.description]) # heading row
        writer.writerows(cursor.fetchall())
    
def export_csv_dialog(query = "select 42 as known_facts"):
    "export csv dialog"
    #Proposed encoding (we favorize utf-8 the only future)
    encodings = ["utf-8",locale.getdefaultlocale()[1],"utf-16","utf-8-sig"]
    if os.name == 'nt':
        encodings = ["utf-8-sig",locale.getdefaultlocale()[1],
                         "utf-16","utf-8"]
    #Proposed csv separator
    default_sep=[",",";"]

    filename_tk = filedialog.asksaveasfile(mode='w',defaultextension='.db',
              title="Choose .csv file name",                          
              filetypes=[("default","*.csv"),("other","*.txt"),("all","*.*")])
    csv_file = filename_tk.name
    filename_tk.close
    if csv_file != "(none)":
        #Request form (see http://www.python-course.eu/tkinter_entry_widgets.php)
        fields = [('csv Name', csv_file )
           ,('column separator',default_sep[0])
           ,('Header line',True)
           ,('Encoding',encodings[0]) ] 
 
        create_dialog(("Export to %s" % csv_file ), fields ,
                  ("Export",  export_csv_ok)                  
                  , ("Data to export (MUST be 1 Request)" ,(query)))

def export_csvtb():
    "get table selected definition and launch cvs export dialog"
    selitems = db_tree.selection()
    if selitems:
        #item_id = db_tree.focus()
        selitem = db_tree.selection()[0]
        action = db_tree.item(selitem, "values")[1]
        if action[-10:] == " limit 999": # remove auto-limit for export
              action = action[:-10] 
        if action != "":
              export_csv_dialog(action)  
              
def export_csvqr():
    "get tab selected definition and launch cvs export dialog"
    nb = n.notebook
    active_tab_id = nb.select()
    #get current selection (or all)
    fw =n.fw_labels[active_tab_id]
    action = ""
    try :
        action = (fw.get('sel.first', 'sel.last')) 
    except:
        action = fw.get(1.0,END)[:-1]   

    if action != "":
              export_csv_dialog(action)   
              
def t_doubleClicked(event):
    "action on dbl_click on the Database structure" 
    selitems = db_tree.selection()
    if selitems:
        instruction = db_tree.item(selitems[0], "values")[0]
        action = db_tree.item(selitems[0], "values")[1]
        default_text = db_tree.item(selitems[0], "text")
        #parent Table
        parent_node =  db_tree.parent(selitems[0])
        parent_text = db_tree.item(parent_node, "text")
        if parent_text[-1] != ")":
            default_text = parent_text
        #create a new tab 
        new_tab_ref = n.new_query_tab(default_text, instruction)
        #run-it
        if action != "":
           run_tab()          

        
def actualize_db():
    "re-build database view"

    #bind double-click for easy user interaction
    db_tree.tag_bind('run', '<Double-1>', t_doubleClicked)
    
    #delete existing tree entries before re-creating them
    for node  in db_tree.get_children():
            db_tree.delete(node )

    #create initial node
    id0 = db_tree.insert("",0,"Database",
                   text=(database_file.replace("\\","/")).split("/")[-1] , 
                   values=(database_file,"")   )

    #add master_table, Tables, Views, Trigger, Index
    for category in ['master_table', 'table', 'view', 'trigger', 'index',
    'pydef']:
        add_things(id0, category)

    #add attached databases, and get back attached table names
    attached =  add_things(id0,'attached_databases' )
    
    #redo for attached database
    for att_db in attached:
        #create initial node for attached table
        id0 = db_tree.insert("",'end', att_db + "(Attached)",
                   text = att_db + " (attached database)", 
                   values = (att_db,"")  )
        #add master_table, Tables, Views, Trigger, Index for each attached db
        for category in ['master_table', 'table', 'view', 'trigger', 'index']:
            add_things(id0, category, att_db +".") 

def quit_db():
   """quit application button"""
   global tk_win 
   messagebox.askyesno(
	   message='Are you sure you want to quit ?',
	   icon='question', title='Install')
   #messagebox.showinfo(message='Have a good day')
   tk_win.destroy()

def create_menu(root):
    menubar = Menu(root)
    root['menu'] = menubar
    
    #feeding the top level menu
    menu_file = Menu(menubar)
    menubar.add_cascade(menu=menu_file, label='Database')

    menu_tools = Menu(menubar)
    menubar.add_cascade(menu=menu_tools, label='Tools')

    menu_help = Menu(menubar)
    menubar.add_cascade(menu=menu_help, label='?')

    #feeding database sub-menu
    menu_file.add_command(label='New Database', command=new_db)
    menu_file.add_command(label='New In-Memory Database', command=new_db_mem)
    menu_file.add_command(label='Connect to Database ...', command=open_db)
    menu_file.add_command(label='Close Database', command=close_db)   
    menu_file.add_separator()
    menu_file.add_command(label='Attach Database', command=attach_db)   
    menu_file.add_separator()
    menu_file.add_command(label='Actualize', command=actualize_db)   
    menu_file.add_separator()
    menu_file.add_command(label='Quit', command=quit_db)   

    #feeding table sub-menu
    menu_tools.add_command(label='Import a CSV file',
                           command=import_csvtb)   
    menu_tools.add_command(label='Export the selected table',
                           command=export_csvtb)   
    menu_tools.add_separator()
    menu_tools.add_command(label="Export the selected request",
                           command=export_csvqr)   
                           
    menu_help.add_command(label='about',command = lambda : messagebox.showinfo(
       message="""Sqlite_py_manager is a small SQLite Browser written in Python
            \n(version 2014-05-10b)
            \n(https://github.com/stonebig/baresql/blob/master/examples)""")) 
#F/Menubar part        
#D/Toolbar part
def get_tk_icons():
    "creates a dictionary of {iconname : icon_image}"

    #to create this base 64 from a toto.gif image of 24x24 size do :
    #    import base64
    #    b64 = base64.encodestring(open("toto.gif","rb").read())
    #    print("'gif_img':'''\\\n" + b64.decode("utf8") + "'''")
    icons = {'run_img':'''\
R0lGODdhGAAYAJkAADOqM////wCqMwAAACwAAAAAGAAYAAACM4SPqcvt7wJ8oU5W8025b9OFW0hO
5EmdKKauSosKL9zJC21FsK27kG+qfUC5IciITConBQA7
'''
    ,'refresh_img':'''\
R0lGODdhGAAYAJkAAP///zOqMwCqMwAAACwAAAAAGAAYAAACSoSPqcvt4aIJEFU5g7AUC9px1/JR
3yYy4LqAils2IZdFMzCP6nhLd2/j6VqHD+1RAQKLHVfC+VwtcT3pNKOTYjTC4SOK+YbH5EYBADs=
'''
    ,'deltab_img':'''\
R0lGODdhGAAYAKoAAP///8zVzP9VAGaAmf//zP9VMwAAAAAAACwAAAAAGAAYAAADVQi63P4wykmF
dVbUzLLeF+B9zGCeZlaMBLWM1uC+I4CiUW0HfB9AMMXA13vALkPir1HzJIkYjsKjXHZCNEF1ltnO
dsovGPp9+sTmYtk7S/PQbJc7kAAAOw==
'''
    ,'deltabresult_img':'''\
R0lGODdhGAAYAJkAAP///5mqmf8AAAAAACwAAAAAGAAYAAACV4wfoMutyZA0DsBF372xzT95XBWN
GSmmqIqN66mtbCy3swxbLprnrwkKAgWCT4MIBBCLmMXSIjIsi4fpYfZUEm0lx/Tm+3bHimxWpxKX
n73E+YgExYXEAgA7
'''
    ,'newtab_img':'''\
R0lGODdhGAAYAJkAAP///8zVzAAAAAAAACwAAAAAGAAYAAACToSPqcvtD6GYkU1R1z2h+2BdogAi
X3eMYsmxrHqxxikb25zQ9A3UaMPz1XJE09BUbDl8uSMnOdOdoD3ph/pjMI1LrBOH5Da2ynHTKk0U
AAA7
'''  }  
    
    #transform in tk icons (avoids the dereferencing problem)
    for key, value in icons.items():
        icons[key] = ttk.tkinter.PhotoImage(data = value)
    # gives back the whished icon in ttk ready format
    return  icons
    
def createToolTip( widget, text ):
    "Creates a tooptip box for a widget."
    #www.daniweb.com/software-development/python/code/234888/tooltip-box
    
    def enter( event ):
        global tipwindow
        x = y = 0
        try :
            tipwindow = tipwindow
        except:
            tipwindow = None
        if tipwindow or not text:
            return
        x, y, cx, cy = widget.bbox( "insert" )
        x += widget.winfo_rootx() + 27
        y += widget.winfo_rooty() + 27
        # Creates a toplevel window
        tipwindow = tw = Toplevel( widget )
        # Leaves only the label and removes the app window
        tw.wm_overrideredirect( 1 )
        tw.wm_geometry( "+%d+%d" % ( x, y ) )
        label = Label( tw, text = text, justify = LEFT,
                       background = "#ffffe0", relief = SOLID, borderwidth = 1,
                       font = ( "tahoma", "8", "normal" ) )
        label.pack( ipadx = 1 )
        
    def close( event ):
        global tipwindow
        tw = tipwindow
        tipwindow = None
        if tw:
            tw.destroy()
            
    widget.bind( "<Enter>", enter )
    widget.bind( "<Leave>", close )    #creating the menu object


def create_toolbar(root):
    "Toolbar of the application"
    toolbar = Frame(tk_win, relief=RAISED)
    toolbar.pack(side=TOP, fill=X)
    global tk_icon #otherwise they are destroyed before display
    tk_icon = get_tk_icons()
    
    #list of image, action, tootip :
    to_show=[('refresh_img', actualize_db, "Refresh Databases")
            ,('run_img', run_tab, "Run Script Selection")
            ,('deltab_img', del_tab, "Delete current tab")
            ,('deltabresult_img', del_tabresult, "Clear tab Result")
            ,('newtab_img', new_tab, "Create a New Tab")]
    
    for bu_def in to_show:
        bu = Button(toolbar, image = tk_icon[bu_def[0]] ,
            command = bu_def[1])
        bu.pack(side=LEFT, padx=2, pady=2); createToolTip(bu, bu_def[2]) 
    
#F/Toolbar part

#D/baresql token editor
class baresql():
    def __init__(self, connection="sqlite://", keep_log = False,
                 cte_inline = True):
        nothing_to_see = 1
 
    def get_token(self, sql, start = 0):
        "return next token type and ending+1 from given sql start position"
        length = len(sql)
        i = start
        token = 'TK_OTHER'
        dico = {' ':'TK_SP', '\t':'TK_SP', '\n':'TK_SP', '\f':'TK_SP',
         '\r':'TK_SP', '(':'TK_LP', ')':'TK_RP', ';':'TK_SEMI', ',':'TK_COMMA',
         '/':'TK_OTHER', "'":'TK_STRING',"-":'TK_OTHER',
         '"':'TK_STRING', "`":'TK_STRING'}
        if length > start:
            if sql[i] == "-" and i < length and sql[i:i+2] == "--" :
                #an end-of-line comment
                token='TK_COM'
                i = sql.find("\n", start) #TK_COM feeding
                if i <= 0:
                    i = length
            elif sql[i] == "/" and i < length and sql[i:i+2] == "/*":
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
                        i += 1
                if token == 'TK_STRING': #TK_STRING feeding
                    delimiter = sql[i]
                    if delimiter == sql[i]:
                        token = 'TK_ID'
                    while (i < length  and sql[i] == delimiter):
                        i += 1 #other (don't bother, case)
        return i, token


    def get_sqlsplit(self, sql, remove_comments=False):
        """split an sql file in list of separated sql orders"""
        beg = end = 0; length = len(sql)
        sqls = []
        while end < length-1:
            tk_end , token = self.get_token(sql,end)
            if token == 'TK_SEMI' or tk_end == length: # end of a single sql
                sqls.append(sql[beg:tk_end])
                beg = tk_end
            if token == 'TK_COM' and remove_comments: # clear comments option
                sql = sql[:end]+' '+ sql[tk_end:]
                length = len(sql)
                tk_end = end + 1
            end = tk_end
        if beg < length :
               sqls.append(sql[beg:])
        return sqls
#F/baresql token editor

if __name__ == '__main__':

    # create a tkk graphic interface
    global tk_win
    
    #With a main window tk_win
    tk_win = Tk()
    tk_win.title('Sqlite_py_manager : browsing SQLite datas on the go')
    tk_win.option_add('*tearOff', FALSE)  # recommanded by tk documentation
    tk_win.minsize(600,200)               # minimal size
    
    #With a Menubar
    create_menu(tk_win)

    #With a Toolbar
    create_toolbar(tk_win)

    #With a Panedwindow of two frames: 'Database' and 'Queries'
    p  = ttk.Panedwindow(tk_win, orient=HORIZONTAL)
    p.pack(fill=BOTH, expand=1)

    f_database = ttk.Labelframe(p, text='Databases', width=200 , height=100)
    p.add(f_database)

    f_queries = ttk.Labelframe(p, text='Queries', width=200, height=100)
    p.add(f_queries)
    
    #build tree view 't' inside the left 'Database' Frame
    db_tree = ttk.Treeview(f_database , displaycolumns = [], 
                           columns = ("detail","action"))

    #create a  notebook 'n' inside the right 'Queries' Frame
    n = notebook_for_queries(f_queries , [])

    db_tree.tag_configure("run")
    db_tree.pack(fill = BOTH , expand = 1)
 
    #Start with a memory Database
    conn_inst={}
    new_db_mem()

    #Propose a Demo
    welcome_text = """-- SQLite Memo (Demo = click on green "->" and "@" icons)
\n-- to CREATE a table 'items' and a table 'parts' :
create table item (ItemNo, Description,Kg  , PRIMARY KEY (ItemNo));
create table part(ParentNo, ChildNo , Description TEXT , Qty_per NUMERIC);
\n-- to CREATE an index :
CREATE INDEX parts_id1 ON part(ParentNo Asc, ChildNo Desc);
\n-- to CREATE a view 'v1':
CREATE VIEW v1 as select * from item inner join part as p ON ItemNo=p.ParentNo;
\n-- to INSERT datas 
INSERT INTO item values("T","Ford",1000),("A","Merced",1250),("W","Wheel",9);
INSERT INTO part select ItemNo,"W","needed",Kg/250*4 from item where Kg>250;
\n-- to CREATE a Python embedded function (enclose them by "py" and ";") :
pydef py_sin(s):
    "sinus function : example loading module, handling input/output as strings"
    import math as py_math 
    return ("%s" %  py_math.sin(s*1));
pydef py_fib(n):
   "fibonacci : example with function call (may only be internal) "
   fib = lambda n: n if n < 2 else fib(n-1) + fib(n-2)
   return("%s" % fib(n*1));
\n-- to USE a python embedded function :
select py_sin(1) as sinus_1, py_fib(8) as fib_8, sqlite_version() ;
\n-- to EXPORT a TABLE 
-- click one TABLE's field, then click on 'Tools->Export the selected table'
\n-- to export a REQUEST's result
-- select the REQUEST aera, then click on 'Tools->Export the selected request', 
-- example : select the end of this line: select sqlite_version()  """
    n.new_query_tab("Welcome", welcome_text )
    
    tk_win.mainloop()

