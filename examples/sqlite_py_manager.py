#!/usr/bin/python
# -*- coding: utf-8 -*-

#v10e : csv window grab focus + show content

import sqlite3 as sqlite 
import sys, os
import csv

from tkinter import *
from tkinter import font
from tkinter import ttk
from tkinter.ttk import *
from tkinter import filedialog
from tkinter import messagebox

global database_file
global conn 

#********* start of tkk part ***********
# applied from tkk presentation of Jeff Armstrong at PyOhio july 2012 :
#      pyvideo.org/category/22/pyohio-2012
# and related source code :
#     https://github.com/ArmstrongJ/presentations/blob/master/pyohio2012 
# and treeview sorting example :
#     http://svn.python.org/projects/python/branches/pep-0384/
#        Demo/tkinter/ttk/treeview_multicolumn.py
# and treeview in a notebook example :
#     http://stackoverflow.com/questions/10776912/
#       tkinter-python-multiple-scrollbars-in-notebook-widget
#********* start of tkk part ***********
def sortby(tree, col, descending):
    """Sort tree contents when a column is clicked on."""
    # grab values to sort
    data = [(tree.set(child, col), child) for child in tree.get_children('')]

    # reorder data
    data.sort(reverse=descending)
    for indx, item in enumerate(data):
        tree.move(item[1], '', indx)

    # switch the heading so that it will sort in the opposite direction
    tree.heading(col,
        command=lambda col=col: sortby(tree, col, int(not descending)))
    
class sqltrees():
    """Create a Notebook with a list in the First frame
       and query results in following treeview frames """
    def __init__(self, root, queries):
        self.root = root
        self.notebook = Notebook(root) #ttk.
        
        self.fw_tabs = {} # tab_tk_id -> python tab object
        self.fw_labels = {} # tab_tk_id -> Scripting frame python object
        self.fw_results = {} # tab_tk_id ->   Results objects
        
        # Resize rules
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        #pfg root.title("sql book")

        #Prepare Welcome informations  with the Numberd list of Queries
        welcome_frame = "Welcome"
        welcome_text = """-- Welcome Frame (with a small memo)
--       CREATE a table  
create table items  (ItemNo, Description,Kg);
create table products(ItemNo TEXT PRIMARY KEY,Description TEXT ,Kg NUMERIC);
--       CREATE an index 
CREATE INDEX items_id1 ON items(ItemNo ASC, Kg Desc);
--       CREATE a view 
CREATE VIEW items_and_product as select * 
   from items as i inner join products as p ON i.ItemNo=p.ItemNo;
--       CREATE a python embedded function  
pydef mysqrt(s):
    return ("%s" %s**.5);
--       USE a python embedded function  
select mysqrt(3), sqlite_version();    
"""
        welcome_columns = ("",)
        welcome_data=[]
        if type(welcome_data)==type('ee'):
            welcome_data=[welcome_data]
        welcome_data=list(enumerate(welcome_data))    


        #Create first Welcome tab  
        self.column_treeview(welcome_frame, welcome_text,
                             welcome_columns, welcome_data)

        ##grid widgets
        self.notebook.grid(row=0, column=0, sticky=(N,W,S,E))

    def column_treeview(self, title, query,columns, data):
        #Add a new frame named 'title' to the notebook 

        #pfg fw_welcome = Frame(self.notebook)
        fw_welcome = ttk.Panedwindow(tk_win, orient=VERTICAL)
        

        fw_welcome.pack(fill = 'both', expand=True)
        self.notebook.add(fw_welcome, text=(title))



        #new "editable" script 
        f1 = ttk.Labelframe(fw_welcome, text='Script', width=200, height=100)
        fw_welcome.add(f1)
        f1.grid_columnconfigure(0, weight=1)
        f1.grid_rowconfigure(0, weight=1) 
        #f1.grid(column=0, row=0, sticky='nsew', in_=fw_welcome )
        #Create a top text box on this new frame, with 'query' definition in it
        #    padding=(10, 2, 10, 6), text=(query))
        fw_label = ttk.tkinter.Text(f1 ,bd =1)
        
        
        scroll = ttk.Scrollbar(f1,   command = fw_label.yview)
        fw_label.configure(yscrollcommand = scroll.set)
        fw_label.insert(END, (query))
        fw_label.pack(side =LEFT, expand =YES, fill =BOTH, padx =2, pady =2)
        #fw_label.grid(column=0, row=0, sticky=(N, S, E, W))
        scroll.pack(side =RIGHT, expand =NO, fill =BOTH, padx =2, pady =2)
        #scroll.grid(column=1, row=0, sticky=(N, S, E, W))
 
        #keep tab reference  by tk id 
        working_tab_id = "." + fw_welcome._name
        #keep tab reference to tab (by tk id)
        self.fw_tabs[working_tab_id]  = fw_welcome        
        #keep tab reference to script (by tk id)
        self.fw_labels[working_tab_id]  = fw_label        
        #keep   reference to result objects (by tk id)
        self.fw_results[working_tab_id]  = []        

        #add a new Result to this notebook pane
        self.add_treeview(fw_welcome,  columns, data)
        #self.remove_treeviews()
        
        #activate this tab print(self.notebook.tabs())
        self.notebook.select(working_tab_id) 

    def remove_treeviews(self, given_tk_id  ):
        """ remove results from given tab tk_id """
        for xx in self.fw_results[given_tk_id]:
            xx.grid_forget()
            xx.destroy()
        self.fw_results[given_tk_id]=[]    
        
    def add_treeview(self, fw_welcome,  columns, data):
        f2 = ttk.Labelframe(fw_welcome, text='Result', width=200, height=100); 
        fw_welcome.add(f2)
        

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
        fw_Box.grid(column=0, row=1, sticky='nsew', in_=f2)
        fw_vsb.grid(column=1, row=1, sticky='ns', in_=f2)
        fw_hsb.grid(column=0, row=2, sticky='new', in_=f2)

        #This new Treeview , which is on row 1 of the new Frame , 
        #will occupy all variable space
        f2_row = (1+len(self.fw_results[working_tab_id]))
        #f2.grid(column=0, row=f2_row, sticky='nsew' , in_=fw_welcome )
        f2.grid_columnconfigure(0, weight=1)
        f2.grid_rowconfigure(f2_row, weight=1) 
        #f2.pack(side =SOUTH, expand =YES, fill =BOTH, padx =2, pady =2)

        #feed list
        for col in tuple(tree_columns):
            fw_Box.heading(col, text=col.title(),
                command=lambda c=col: sortby(fw_Box, c, 0))
            # XXX tkFont.Font().measure expected args are incorrect according
            #     to the Tk docs
            fw_Box.column(col, width=font.Font().measure(col.title()))

        for items in data:
            #cas string
            item=items
            if type(item)==type('ee'):
                item=(items,)
            #replace line_return by space via a lambda
            
            clean = lambda T: T.replace("\n"," ") if type(T)==type('ee') else T
            line_cells=tuple(clean(item[c]) for c  in range(len(tree_columns)))            
            
            fw_Box.insert('', 'end', values=line_cells)
            # adjust columns length if necessary
            for indx, val in enumerate(line_cells):
                try :
                    ilen = font.Font().measure(val)
                
                    if fw_Box.column(tree_columns[indx], width=None
                        ) < ilen and ilen<400 :
                        fw_Box.column(tree_columns[indx], width=ilen)
                except:
                    pass
         
def get_tk_icons():
    "gives back the image of the whished icon "

    #Inlined base 64 icons are created via the following procedure
    # 1-create a toto.gif image of 24x24 size (for this example)
    # 2-apply this transformation step : 
    #    import base64
    #    gif_file = r"C:\Users\...\gif_file.gif"
    #    b64 = base64.encodestring(open(gif_file,"rb").read())
    #    print('gif_img':'''\\\n" + b64.decode("utf8") + "'''")
    # 3-copy/paste the result in the code of your program as below

    icons = {'run_img':'''\
R0lGODlhEQARAHAAACH5BAEAAPwALAAAAAARABEAhwAAAAAAMwAAZgAAmQAAzAAA/wArAAArMwAr
ZgArmQArzAAr/wBVAABVMwBVZgBVmQBVzABV/wCAAACAMwCAZgCAmQCAzACA/wCqAACqMwCqZgCq
mQCqzACq/wDVAADVMwDVZgDVmQDVzADV/wD/AAD/MwD/ZgD/mQD/zAD//zMAADMAMzMAZjMAmTMA
zDMA/zMrADMrMzMrZjMrmTMrzDMr/zNVADNVMzNVZjNVmTNVzDNV/zOAADOAMzOAZjOAmTOAzDOA
/zOqADOqMzOqZjOqmTOqzDOq/zPVADPVMzPVZjPVmTPVzDPV/zP/ADP/MzP/ZjP/mTP/zDP//2YA
AGYAM2YAZmYAmWYAzGYA/2YrAGYrM2YrZmYrmWYrzGYr/2ZVAGZVM2ZVZmZVmWZVzGZV/2aAAGaA
M2aAZmaAmWaAzGaA/2aqAGaqM2aqZmaqmWaqzGaq/2bVAGbVM2bVZmbVmWbVzGbV/2b/AGb/M2b/
Zmb/mWb/zGb//5kAAJkAM5kAZpkAmZkAzJkA/5krAJkrM5krZpkrmZkrzJkr/5lVAJlVM5lVZplV
mZlVzJlV/5mAAJmAM5mAZpmAmZmAzJmA/5mqAJmqM5mqZpmqmZmqzJmq/5nVAJnVM5nVZpnVmZnV
zJnV/5n/AJn/M5n/Zpn/mZn/zJn//8wAAMwAM8wAZswAmcwAzMwA/8wrAMwrM8wrZswrmcwrzMwr
/8xVAMxVM8xVZsxVmcxVzMxV/8yAAMyAM8yAZsyAmcyAzMyA/8yqAMyqM8yqZsyqmcyqzMyq/8zV
AMzVM8zVZszVmczVzMzV/8z/AMz/M8z/Zsz/mcz/zMz///8AAP8AM/8AZv8Amf8AzP8A//8rAP8r
M/8rZv8rmf8rzP8r//9VAP9VM/9VZv9Vmf9VzP9V//+AAP+AM/+AZv+Amf+AzP+A//+qAP+qM/+q
Zv+qmf+qzP+q///VAP/VM//VZv/Vmf/VzP/V////AP//M///Zv//mf//zP///wAAAAAAAAAAAAAA
AAigAPcJHEiwoEGBQ9oMGXKQYEJo+iDyYHhwSERlnugkg6aMh8E2yqB58jTHUyeN0HoUtEiSlKd9
dObMUWbDob5SI0kKpNPGE7SaAntAwzTH4Jw2pW4MPAOt5Mc5n4Du4wHt05yYRfe1SUJHGQOCQo/y
1DpnSDKpAm1UPXo0SZtPpWIYtLHR05A5bkol+3rQRoNkeuPybbivAYwGaAkrXnwwIAA7
''' 
    ,'refresh_img':'''\
R0lGODlhEQARAHAAACH5BAEAAPwALAAAAAARABEAhwAAAAAAMwAAZgAAmQAAzAAA/wArAAArMwAr
ZgArmQArzAAr/wBVAABVMwBVZgBVmQBVzABV/wCAAACAMwCAZgCAmQCAzACA/wCqAACqMwCqZgCq
mQCqzACq/wDVAADVMwDVZgDVmQDVzADV/wD/AAD/MwD/ZgD/mQD/zAD//zMAADMAMzMAZjMAmTMA
zDMA/zMrADMrMzMrZjMrmTMrzDMr/zNVADNVMzNVZjNVmTNVzDNV/zOAADOAMzOAZjOAmTOAzDOA
/zOqADOqMzOqZjOqmTOqzDOq/zPVADPVMzPVZjPVmTPVzDPV/zP/ADP/MzP/ZjP/mTP/zDP//2YA
AGYAM2YAZmYAmWYAzGYA/2YrAGYrM2YrZmYrmWYrzGYr/2ZVAGZVM2ZVZmZVmWZVzGZV/2aAAGaA
M2aAZmaAmWaAzGaA/2aqAGaqM2aqZmaqmWaqzGaq/2bVAGbVM2bVZmbVmWbVzGbV/2b/AGb/M2b/
Zmb/mWb/zGb//5kAAJkAM5kAZpkAmZkAzJkA/5krAJkrM5krZpkrmZkrzJkr/5lVAJlVM5lVZplV
mZlVzJlV/5mAAJmAM5mAZpmAmZmAzJmA/5mqAJmqM5mqZpmqmZmqzJmq/5nVAJnVM5nVZpnVmZnV
zJnV/5n/AJn/M5n/Zpn/mZn/zJn//8wAAMwAM8wAZswAmcwAzMwA/8wrAMwrM8wrZswrmcwrzMwr
/8xVAMxVM8xVZsxVmcxVzMxV/8yAAMyAM8yAZsyAmcyAzMyA/8yqAMyqM8yqZsyqmcyqzMyq/8zV
AMzVM8zVZszVmczVzMzV/8z/AMz/M8z/Zsz/mcz/zMz///8AAP8AM/8AZv8Amf8AzP8A//8rAP8r
M/8rZv8rmf8rzP8r//9VAP9VM/9VZv9Vmf9VzP9V//+AAP+AM/+AZv+Amf+AzP+A//+qAP+qM/+q
Zv+qmf+qzP+q///VAP/VM//VZv/Vmf/VzP/V////AP//M///Zv//mf//zP///wAAAAAAAAAAAAAA
AAifAAEIHLiv4D6BBREORPjjR44fBSEqHBgtRzRl0aIBsZPjIACPH3FEgxPKiJFQyyx4XJkDDo4c
OUAdOQlkJUIfEAs+CMVT5cR9HT8+/AHEQk2FBpMqtbnPKBAIPx4cBApyKpBQp0Ll3PcDR9WPV40c
AZWjAg5NQZFW4GkyFKhQDkB+/KhD04+3msgmJPgxp8OGcpGuNLiQb+HDC5cqVhoQADs=
'''
    ,'deltab_img':'''\
R0lGODlhGAAYAHAAACH5BAEAAPwALAAAAAAYABgAhwAAAAAAMwAAZgAAmQAAzAAA/wArAAArMwAr
ZgArmQArzAAr/wBVAABVMwBVZgBVmQBVzABV/wCAAACAMwCAZgCAmQCAzACA/wCqAACqMwCqZgCq
mQCqzACq/wDVAADVMwDVZgDVmQDVzADV/wD/AAD/MwD/ZgD/mQD/zAD//zMAADMAMzMAZjMAmTMA
zDMA/zMrADMrMzMrZjMrmTMrzDMr/zNVADNVMzNVZjNVmTNVzDNV/zOAADOAMzOAZjOAmTOAzDOA
/zOqADOqMzOqZjOqmTOqzDOq/zPVADPVMzPVZjPVmTPVzDPV/zP/ADP/MzP/ZjP/mTP/zDP//2YA
AGYAM2YAZmYAmWYAzGYA/2YrAGYrM2YrZmYrmWYrzGYr/2ZVAGZVM2ZVZmZVmWZVzGZV/2aAAGaA
M2aAZmaAmWaAzGaA/2aqAGaqM2aqZmaqmWaqzGaq/2bVAGbVM2bVZmbVmWbVzGbV/2b/AGb/M2b/
Zmb/mWb/zGb//5kAAJkAM5kAZpkAmZkAzJkA/5krAJkrM5krZpkrmZkrzJkr/5lVAJlVM5lVZplV
mZlVzJlV/5mAAJmAM5mAZpmAmZmAzJmA/5mqAJmqM5mqZpmqmZmqzJmq/5nVAJnVM5nVZpnVmZnV
zJnV/5n/AJn/M5n/Zpn/mZn/zJn//8wAAMwAM8wAZswAmcwAzMwA/8wrAMwrM8wrZswrmcwrzMwr
/8xVAMxVM8xVZsxVmcxVzMxV/8yAAMyAM8yAZsyAmcyAzMyA/8yqAMyqM8yqZsyqmcyqzMyq/8zV
AMzVM8zVZszVmczVzMzV/8z/AMz/M8z/Zsz/mcz/zMz///8AAP8AM/8AZv8Amf8AzP8A//8rAP8r
M/8rZv8rmf8rzP8r//9VAP9VM/9VZv9Vmf9VzP9V//+AAP+AM/+AZv+Amf+AzP+A//+qAP+qM/+q
Zv+qmf+qzP+q///VAP/VM//VZv/Vmf/VzP/V////AP//M///Zv//mf//zP///wAAAAAAAAAAAAAA
AAiyAPcJHEiwoMGDAvUVVJgQoUOGDhGWI1fOIEVyEQWW24hx4MZy3jJq5CjQ28SN+yDuSzNpEsuX
FMt9i7lRZcaTHMulEUnw48l9Llu+nOTwIkqgyoglXSrxI0WBaZQq/aT0oFGnSKkuJWbQZ0Wak7Yq
y6TM4k+NMclqTdr1qEeKUpVp5bnvo1hin+hCxTuWqd6wcanqRYo37uCoypLO/UuWrF+6gJeSHTxJ
ad+qetNcTkwsIAA7
'''
    ,'deltabresult_img':'''\
R0lGODlhGAAYAHAAACH5BAEAAPwALAAAAAAYABgAhwAAAAAAMwAAZgAAmQAAzAAA/wArAAArMwAr
ZgArmQArzAAr/wBVAABVMwBVZgBVmQBVzABV/wCAAACAMwCAZgCAmQCAzACA/wCqAACqMwCqZgCq
mQCqzACq/wDVAADVMwDVZgDVmQDVzADV/wD/AAD/MwD/ZgD/mQD/zAD//zMAADMAMzMAZjMAmTMA
zDMA/zMrADMrMzMrZjMrmTMrzDMr/zNVADNVMzNVZjNVmTNVzDNV/zOAADOAMzOAZjOAmTOAzDOA
/zOqADOqMzOqZjOqmTOqzDOq/zPVADPVMzPVZjPVmTPVzDPV/zP/ADP/MzP/ZjP/mTP/zDP//2YA
AGYAM2YAZmYAmWYAzGYA/2YrAGYrM2YrZmYrmWYrzGYr/2ZVAGZVM2ZVZmZVmWZVzGZV/2aAAGaA
M2aAZmaAmWaAzGaA/2aqAGaqM2aqZmaqmWaqzGaq/2bVAGbVM2bVZmbVmWbVzGbV/2b/AGb/M2b/
Zmb/mWb/zGb//5kAAJkAM5kAZpkAmZkAzJkA/5krAJkrM5krZpkrmZkrzJkr/5lVAJlVM5lVZplV
mZlVzJlV/5mAAJmAM5mAZpmAmZmAzJmA/5mqAJmqM5mqZpmqmZmqzJmq/5nVAJnVM5nVZpnVmZnV
zJnV/5n/AJn/M5n/Zpn/mZn/zJn//8wAAMwAM8wAZswAmcwAzMwA/8wrAMwrM8wrZswrmcwrzMwr
/8xVAMxVM8xVZsxVmcxVzMxV/8yAAMyAM8yAZsyAmcyAzMyA/8yqAMyqM8yqZsyqmcyqzMyq/8zV
AMzVM8zVZszVmczVzMzV/8z/AMz/M8z/Zsz/mcz/zMz///8AAP8AM/8AZv8Amf8AzP8A//8rAP8r
M/8rZv8rmf8rzP8r//9VAP9VM/9VZv9Vmf9VzP9V//+AAP+AM/+AZv+Amf+AzP+A//+qAP+qM/+q
Zv+qmf+qzP+q///VAP/VM//VZv/Vmf/VzP/V////AP//M///Zv//mf//zP///wAAAAAAAAAAAAAA
AAjFAJURE0hwn8GDCBMaJJZwoEOCDhXu+5RQWaaDFjFKZIgwk8BPxEBazKhQWUWPD1NCFMjx4ECJ
MD9RRAgS5saWC03arKgT48WdCInh3PcS6EGZJ0d6XKp0pNCGysqVA1qOnLKeBmvuk0puqkGuXp8G
xfq1a0myAg12Nfu1atihINnarHoV6kqVKYcq0zRSUzJioIYFBhUScN2xcmFWFXvwb1mvB90aVJYs
Id+EXSUH1TsULOTJZD0+TqhZKOG/V4kllthVWUAAOw==
'''
    }  
    
    #transform in tk icons (avoids the dereferencing problem)
    for key, value in icons.items():
        icons[key] = ttk.tkinter.PhotoImage(data = value)
    # gives back the whished icon in ttk ready format
    return  icons
#********* end of tkk part ***********



#tree objet subfunctions
def add_things(root_id, what, sql_definition = ""):
    #add Tables (sort order, name, sql)
    sql = ("""SELECT name, name, sql FROM sqlite_master 
     WHERE type='%s' order by name;""" % what)
    if not sql_definition == "":
        sql = sql_definition
    cursor = conn.execute(sql )
    tables = cursor.fetchall()
    cursor.close

    idt = t.insert(root_id,"end",what,text="%s (%s)" % (what, len(tables)) ,
                   values=(conn,) )
    for   tab in tables:
        idc = t.insert(idt,"end",tab[0],text=tab[1],
                  values=(conn,))
        sql = "SELECT * FROM  [%s] limit 0;" % tab[1]
        columns=['(Definition)']
        definition = tab[2]
        if sql_definition == "PRAGMA database_list":
            definition = "ATTACH DATABASE '%s' as '%s'"%(tab[2],tab[1])
        t.insert(idc,"end",("%s.%s" % (tab[1], -1)),
                 text=columns[0],tags=('ttk', 'simple'),
                 values=(definition,))
        try :
            cursor = conn.execute(sql )
            columns = [col_desc[0] for col_desc in cursor.description]
            cursor.close
            definition=("select * from [%s]" %tab[1])
            for c in range(len(columns)):
                t.insert(idc,"end",("%s.%s" % (tab[1], c)),
                     text=columns[c],tags=('ttk', 'simple'),
                     values=(definition,))
        except :
            pass

#menu part
def new_db():
   """create a new database"""
   global database_file
   global conn
   import sqlite3 as sqlite 
   filename_tk = filedialog.asksaveasfile(mode='w',defaultextension='.db',
              title="Define a new database name and location",                          
              filetypes=[("default","*.db"),("other","*.db*"),("all","*.*")])
   filename = filename_tk.name
   filenametk.close
   if   filename != "(none)":
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
   print(filename)
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
       t.delete("Database")
   except :
       pass
   conn.close
   
def run_tab():
   #get active notebook tab
   nb = n.notebook
   
   active_tab_id = nb.select()
   active_tab_number = nb.index(nb.select())
   active_tab_name = nb.tab(nb.select(), "text")
   
   #remove previous results
   n.remove_treeviews(active_tab_id)
   #get current selection (or all)
   fw =n.fw_labels[active_tab_id]
   script = ""
   try :
       script = (fw.get('sel.first', 'sel.last')) 
   except:
       script = fw.get(1.0,END)[:-1]   
   print(script)
   create_and_add_results(script, active_tab_id)
   #workaround bug http://bugs.python.org/issue17511 (for python <=3.3.2)
   #otherwise the focus is still set but not shown
   fw.focus_set()

def create_and_add_results(instructions, tab_tk_id):
    nb = n.notebook
    tab_object = n.fw_tabs[tab_tk_id]
    jouer=baresql()
    a_jouer= jouer.get_sqlsplit(instructions, remove_comments = True) 
    for instruction in a_jouer:
        instruction = instruction.replace(";","").strip(' \t\n\r')
        print('jouer ', instruction)
        rows=[]
        rowtitles=("#N/A",)
        if instruction == "":
            #do nothing
            do_nothing = True
        
        elif instruction[:5] == "pydef" :
            instruction = instruction.strip('; \t\n\r')
            print(instruction[2:])
            exec(instruction[2:]  , globals() , locals())
            firstline=(instruction[5:].splitlines()[0]).lstrip()
            firstline = firstline.replace(" ","") + "(" 
            instr_name=firstline.split("(",1)[0].strip()
            instr_parms=firstline.count(',')+1
            instr_add = "conn.create_function('%s', %s, %s)" %(
               instr_name,instr_parms, instr_name)
            print(instr_add)
            exec(instr_add , globals() , locals())
            rowtitles=("Creating embedded python function",)
            for i in (instruction[2:].splitlines()) :
               rows.append((i,))             
            rows.append((instr_add,))
        else:
          try :
            cur = conn.execute(instruction)
            my_curdescription=cur.description
            rows = cur.fetchall()
            #A query may have no result( like for an "update")
            if    cur.description != None :
                rowtitles = [row_info[0] for row_info in cur.description]
                #print (rowtitles)
                #for row in rows:
                #    print (row)
                #show one frame per query result
            cur.close
          except:
            pass
        
        #end of one sql
        if rowtitles != ("#N/A",) :#rows!=[]  :
              n.add_treeview(tab_object, rowtitles, rows )

def del_tabresult():
   #get active notebook tab
   nb = n.notebook
   
   active_tab_id = nb.select()
   n.remove_treeviews(active_tab_id)




def del_tab():
   #get active notebook tab
   nb = n.notebook
   
   active_tab_id = nb.select()
   active_tab_number = nb.index(nb.select())
   print("active_tab_id",active_tab_id)
   print("active_tab_number",active_tab_number)
   active_tab_name = nb.tab(nb.select(), "text")
   print("removing tab [%s]" % active_tab_name)
   #get current selection (or all)
   print("nb.select()",nb.select())
   print("",nb.index('current'))
   nb.forget(nb.select() )

def attach_db():
   """attach an existing database"""
   global database_file
   global conn
   import sqlite3 as sqlite 
   filename = filedialog.askopenfilename(defaultextension='.db',
              title="Choose a database to attach ",    
              filetypes=[("default","*.db"),("other","*.db*"),("all","*.*")])
   attach = ((filename.replace("\\","/")).split("/")[-1]).split(".")[0]
   print(filename, " " , attach)
   if   filename != "(none)":
       attach_order = "ATTACH DATABASE '%s' as '%s' "%(filename,attach);
       cur = conn.execute(attach_order)
       cur.close
       actualize_db()
       print("coucou")

def copy_db():
   print("coucou")
def export_tb():
   print("coucou")
def export_db():
   print("coucou")
def export_st():
   print("coucou")
def import_db():
   print("coucou")


def import_csvtb_ok(thetop, entries):
    #file, table, separator, header, create, replace_data   
    actualize_db()
    for entry in entries:
        field = entry[0]
        text  = entry[1].get()
        print('%s: "%s"' % (field, text)) 

    csv_file = entries[0][1].get().strip()
    table_name = entries[1][1].get().strip()
    separ = entries[2][1].get()
    header = entries[3][1].get()
    creation = entries[4][1].get()
    replacing = entries[5][1].get()
    if   csv_file != "(none)" and len(csv_file)*len(table_name)*len(separ)>1:
       thetop.destroy()
       curs = conn.cursor()
       reader = csv.reader(open(csv_file, 'r'),
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
def import_csvtb():
   """import a csv table with header"""
   global conn
   global tk_win
   import sqlite3 as sqlite 
   csv_file = filedialog.askopenfilename(defaultextension='.db',
              title="Choose a csv file (with header) to import ",
              filetypes=[("default","*.csv"),("other","*.txt"),("all","*.*")])
   top = Toplevel()
   top.title("Importing %s" % csv_file )

   #msg = Message(top, text=about_message)
   #msg.pack()

   #button = Button(top, text="Dismiss", command=top.destroy)
   #button.pack()
   content = ttk.Frame(top)
   frame = ttk.LabelFrame(content, borderwidth=5,  text='first 2 lines '
    ,relief="sunken", width=100, height=100)
   
   #http://www.python-course.eu/tkinter_entry_widgets.php
   fields = [
       ('csv Name', csv_file )
      ,('table Name',(csv_file.replace("\\","/")).split("/")[-1].split(".")[0])
      ,('column separator',';')
      ,('Header line',True)
      ,('Create table',True)
      ,('Replace existing data',True)
      ] 
   nb_fields=len(fields)
   

   content.grid(column=0, row=0, sticky=(N, S, E, W))
   
   frame.grid(column=2, row=0, columnspan=1, rowspan=nb_fields+1,
              sticky=(N, S, E, W))

   #text of file
   fw_label = ttk.tkinter.Text(frame ,bd =1)
   fw_label.pack(side =LEFT)     
   scroll = ttk.Scrollbar(frame,   command = fw_label.yview)
   scroll.pack(side =RIGHT, fill =Y)
   fw_label.configure(yscrollcommand = scroll.set)
   with open(csv_file) as f:
    line1 = f.readline(2222)
    line2 = f.readline(2222)
    fw_label.insert(END, line1 +'\n'+ line2)
   fw_label.config(state=DISABLED)
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
          entries.append((field[0], name_var))
      else :
          namelbl = ttk.Label(content,   text=field[0] )
          namelbl.grid(column=0, row=ta_col, sticky=(N, E), pady=5, padx=5)
          name_var = StringVar()
          name = ttk.Entry(content, textvariable = name_var)
          name_var.set(field[1])
          name.grid(column=1, row=ta_col,   sticky=(N, E, W), pady=5, padx=5)
          entries.append((field[0], name_var))
   
   okbutton = ttk.Button(content, text="Import", 
            command= lambda a=top, b=entries: import_csvtb_ok(a, b))
   cancelbutton = ttk.Button(content, text="Cancel", command=top.destroy)

   okbutton.grid(column=0, row=len(entries))
   cancelbutton.grid(column=1, row=len(entries))
   for x in range(3):
       Grid.columnconfigure(content, x,weight=1)
   for y in range(3):
       Grid.rowconfigure( content, y, weight=1)
   
   top.grab_set()



def t_doubleClicked(event):
    selitems = t.selection()
    if selitems:
        selitem = selitems[0]
        #item_id = t.focus()
        text = t.item(selitem, "text")
        instruction = t.item(selitem, "values")[0]
        #parent Table
        parent_node =  t.parent(selitem)
        parent_table = t.item(parent_node, "text")
        #print(instruction)
        #print(selitem)
        #print(text)
        rows=("",)
        rowtitles=("#N/A",)
        try :
            cur = conn.execute(instruction)
            my_curdescription=cur.description
            rows = cur.fetchall()
            #A query may have no result( like for an "update")
            if    cur.description != None :
                rowtitles = [row_info[0] for row_info in cur.description]
                #print (rowtitles)
                #for row in rows:
                #    print (row)
                #show one frame per query result
        except:
            pass
        n.column_treeview(parent_table, instruction , rowtitles, rows)
        
def actualize_db():
    #"db", "type", "name", "detail"
    print("refresh " , database_file)


    #bind double-click
    t.tag_bind('ttk', '<Double-1>', t_doubleClicked)
    #t.delete(database_file)
    try :
        t.delete("Database")
    except :
        pass
    id0 = t.insert("",0,"Database",
                   text=(database_file.replace("\\","/")).split("/")[-1] , 
                   values=(database_file)   )

    #add the master
    add_things(id0,'master_table', """
     SELECT 'sqlite_master', 'sqlite_master', 'sqlite_master' """)
    
    #add Tables
    add_things(id0, 'table')

    #add Views
    add_things(id0, 'view')

    #add Trigger
    add_things(id0, 'trigger')

    #add Index
    add_things(id0, 'index')

    #add attached databases
    add_things(id0,'attached_databases', "PRAGMA database_list")
    

    



def reconnect_db():
   print("coucou")
def quit_db():
   #"yes" or "no"
   messagebox.askyesno(
	   message='Are you sure you want to quit ?',
	   icon='question', title='Install')
   messagebox.showinfo(message='Have a good day')
def create_tb():
   print("coucou")
def delete_tb():
   print("coucou")
def clear_tb():
   print("coucou")

def rename_tb():
   print("coucou")

def copy_tb():
   print("coucou")


def rebuild_tb():
   print("coucou")


def import_csv():
   print("coucou")



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
        "split an sql file in list of separated sql orders"
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

    global tk_win
    # create a tkk graphic interface
    # with menu, toolbar, left 'Database' Frame, right 'Queries' Notebook 

    #create main window tk_win
    tk_win = Tk()
    tk_win.title('sqlite python browser') # window Title
    tk_win.option_add('*tearOff', FALSE)  # recommanded by tk documentation
    tk_win.minsize(600,200)               # minimal size
    
    #creating the menu object
    menubar = Menu(tk_win)
    tk_win['menu'] = menubar
    
    #feeding the top level menu
    menu_file = Menu(menubar)
    menubar.add_cascade(menu=menu_file, label='Database')

    menu_table = Menu(menubar)
    menubar.add_cascade(menu=menu_table, label='Table')

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
    menu_table.add_command(label='Import CSV table (with header)',
                           command=import_csvtb)   

    #Toolbar will be on TOP of the window (below the menu)
    toolbar = Frame(tk_win,   relief=RAISED)
    toolbar.pack(side=TOP, fill=X)
    tk_icon = get_tk_icons()
    
    #add refresh_button
    Button(toolbar, image = tk_icon['refresh_img'] ,
            command=actualize_db).pack(side=LEFT, padx=2, pady=2)
    
    #add run button 
    Button(toolbar, image = tk_icon['run_img'] ,
            command=run_tab).pack(side=LEFT, padx=2, pady=2)

    #add dell_tab_button
    Button(toolbar, image = tk_icon['deltab_img'] ,
            command=del_tab).pack(side=LEFT, padx=2, pady=2)

    #add dell_tabresult_button
    Button(toolbar, image = tk_icon['deltabresult_img'] ,
            command=del_tabresult).pack(side=LEFT, padx=2, pady=2)

    #create a paned window 'p' that contains 2 frames : 'Database', 'Queries'
    # 'p' layout is managed by pack()
    p  = ttk.Panedwindow(tk_win, orient=HORIZONTAL)
    p.pack(fill=BOTH, expand=1)

    f_database = ttk.Labelframe(p, text='Databases', width=200 , height=100)
    p.add(f_database)

    f_queries = ttk.Labelframe(p, text='Queries', width=200, height=100)
    p.add(f_queries)
    
    #build tree view 't' inside the left 'Database' Frame
    t = ttk.Treeview(f_database , displaycolumns = [], columns = ("detail"))

    #create a  notebook 'n' inside the right 'Queries' Frame
    n = sqltrees(f_queries , [])

    t.tag_configure("ttk")
    t.pack(fill = BOTH , expand = 1)
 

    #Start with a memory Database
    new_db_mem()
    
    tk_win.mainloop()

