#!/usr/bin/python
# -*- coding: utf-8 -*-
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
        
        #activate this tab print(self.notebook.tabs())
        self.notebook.select(working_tab_id) 

        return working_tab_id #gives back tk_id reference of the new tab

    def remove_treeviews(self, given_tk_id  ):
        "remove results from given tab tk_id"
        for xx in self.fw_results[given_tk_id]:
            xx.grid_forget()
            xx.destroy()
        self.fw_results[given_tk_id]=[]    
        
    def add_treeview(self, given_tk_id,  columns, data):
        "add a dataset result to the given tab tk_id"
        fw_welcome = self.fw_tabs[given_tk_id]
        f2 = ttk.Labelframe(fw_welcome, 
              text=('Result (%s lines)' % len(data)), width=200, height=100) 
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
            # tkFont.Font().measure expected args are incorrect according
            #     to the Tk docs
            fw_Box.column(col, width=font.Font().measure(col.title()))

        for items in data:
            #cas string
            item=items
            if type(item)==type('ee'):
                item=(items,)
            #replace line_return by space via a lambda
            
            clean = lambda x: x.replace("\n"," ") if type(x)==type('ee') else x
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
AAhTAIcIHEiwoMGDCBMqXKhwH8OF+yI+RBix4sSCFTNeFJix48WOIB+CHAlxJEmKJk8aTEkyw0qW
GV0ehCmxIUuZNlUy1Cky5kaONX9yFEq0qNGHAQEAOw==
'''
    ,'refresh_img':'''\
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
AAiXAPcJHEiwoMGDCBMqHKKwoUANDAlGdChwCJEMBDNcpKjxA5GJAj9qUKjRokaMBCGClEjEY8mD
QyAajMkwg5KVBJOMLChz38aFOx9OxGmwZ8WgFC0S/Ehx4E+BGh2i3BfV6VSESvcZHRgz4cl9Q7oW
/HjV6RAQJokghKg2I82WbRGiLVtya8KLIM8STYgUbN+mEgELHnwwIAA7
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
AAh7APcJHEiwoMGDCBMqXMjQm0ODDr01jEgwosSJD/dZvEgwjcePHiN+26iP4cCNDtOYPLlxH0iQ
CVu6VEazpjKEKAWmsVnzIMqHO3neLNjSYlCeECkKtCh0aMWMLL01XRlx6sqZQq9iRXr1qE2tXnt2
tboyLE2wZE2aVRYQADs=
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
AAiCADMJHJhpn8GDCBMaLIiQoEOBCvcxPAhx4cSJDRM+3PhQI8aIDT9WBOmxJEmTFD+eHGnxJEqL
HGN6lCbNJU2WEhnSrIlwZ8uQCXfSfJkzqFCiFX32HFo0JFOSN0XGlOmUJ1RpOJM+Nag060ehVn+m
NKp0LNB9Zbky9bo1YtSpcAUGBAA7
'''
    ,'newtab_img':'''\
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
AAiBAJUJHKhsn8GDCPcBWHiwIEKCAhMqZGjQYUOLFg8uBNAwIUSHG0NuzLjvo0CRIklGTIgypEqS
LCmW9AgT4caOD2tqlPlS4kOPNE0SBJpT6ECiF33iXFpRZ0WkTZU+/ZlT6kyqSaWqDGp0a1WtUEs6
vcpUrFWvWZWijQq2aNePCQMCADs=
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

    idt = db_tree.insert(root_id,"end",what,text="%s (%s)" % (what, 
                         len(tables)) , values=(conn,) )
    for   tab in tables:
        idc = db_tree.insert(idt,"end",tab[0],text=tab[1],
                  values=(conn,))
        sql = "SELECT * FROM  [%s] limit 0;" % tab[1]
        columns=['(Definition)']
        definition = tab[2]
        if sql_definition == "PRAGMA database_list":
            definition = "ATTACH DATABASE '%s' as '%s'"%(tab[2],tab[1])
        db_tree.insert(idc,"end",("%s.%s" % (tab[1], -1)),
                 text=columns[0],tags=('ttk', 'simple'),
                 values=(definition,))
        try :
            cursor = conn.execute(sql )
            columns = [col_desc[0] for col_desc in cursor.description]
            cursor.close
            definition=("select * from [%s] limit 999" %tab[1])
            for c in range(len(columns)):
                db_tree.insert(idc,"end",("%s.%s" % (tab[1], c)),
                     text=columns[c],tags=('ttk', 'simple'),
                     values=(definition,))
        except :
            pass

#F/menu actions part
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
   print(script)
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
        rows=[]
        rowtitles=("#N/A",)
        if instruction == "":
            #do nothing
            do_nothing = True
        
        elif instruction[:5] == "pydef" :
            instruction = instruction.strip('; \t\n\r')

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
        else:
          try :
            cur = conn.execute(instruction)
            my_curdescription=cur.description
            rows = cur.fetchall()
            #A query may have no result( like for an "update")
            if    cur.description != None :
                rowtitles = [row_info[0] for row_info in cur.description]
            cur.close
          except:
            pass
        
        #end of one sql
        if rowtitles != ("#N/A",) :#rows!=[]  :
              n.add_treeview(tab_tk_id, rowtitles, rows )

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
   print(filename, " " , attach)
   if   filename != "(none)":
       attach_order = "ATTACH DATABASE '%s' as '%s' "%(filename,attach);
       cur = conn.execute(attach_order)
       cur.close
       actualize_db()
       print("coucou")

def import_csvtb_ok(thetop, entries):
    "read input values from tk formular"
    #file, table, separator, header, create, replace_data   

    csv_file = entries[0][1].get().strip()
    table_name = entries[1][1].get().strip()
    separ = entries[2][1].get()
    header = entries[3][1].get()
    creation = entries[4][1].get()
    replacing = entries[5][1].get()
    encoding_is = entries[6][1].get()
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
       
def import_csvtb():
    """import a csv table with header (suggesting encoding and separator)"""
    global conn
    global tk_win
    import sqlite3 as sqlite 
    import locale
    csv_file = filedialog.askopenfilename(defaultextension='.db',
              title="Choose a csv file (with header) to import ",
              filetypes=[("default","*.csv"),("other","*.txt"),("all","*.*")])

    #Guessing encoding
    with open(csv_file, "rb") as f:
        data = f.read(5)
    if data.startswith(b"\xEF\xBB\xBF"): # UTF-8 "BOM"
        encodings = ["utf-8-sig"]
    elif data.startswith(b"\xFF\xFE") or data.startswith(b"\xFE\xFF"): # UTF-16
        encodings = ["utf16"]
    else:
        encodings = [locale.getdefaultlocale()[1], "utf8"]


    #Guessing csv separator
    #function to try to guess the separator
    def splitcsv(csv_in, separator = ",", string_limit = "'"):
        "split a csv string respecting string delimiters"
        x = csv_in.split(string_limit)
        if len(x) == 1 : #Basic situation of 1 column
            return csv_in.split(separator)
        else:
            #Replace active separators per "<µ²é£>" , then split on "<µ²é£>" 
            for i in range(0,len(x), 2):
                x[i] = x[i].replace(separator, "<µ²é£>")
            return string_limit.join(x).split("<µ²é£>")

    with open(csv_file, encoding = encodings[0]) as f:
        line1 = f.readline(2222)
        line2 = f.readline(2222)
    default_sep=","
    nb_default = len(splitcsv(line1, ",", '"'))
    nb_semi = len(splitcsv(line1, ";", '"'))
    if nb_semi> nb_default and len(splitcsv(line2, ";", '"')) == nb_semi :
        #more semicolumn than comas, and numbers equal on first to lines
        default_sep = ";"

    #Defining the formular fields
    #http://www.python-course.eu/tkinter_entry_widgets.php
    fields = [
        ('csv Name', csv_file )
       ,('table Name',(csv_file.replace("\\","/")).split("/")[-1].split(".")[0])
       ,('column separator',default_sep)
       ,('Header line',True)
       ,('Create table',True)
       ,('Replace existing data',True)
       ,('Encoding',encodings[0])
       ] 
    nb_fields=len(fields)

    #Drawing the request form 
    top = Toplevel()
    top.title("Importing %s" % csv_file )

    content = ttk.Frame(top)
    frame = ttk.LabelFrame(content, borderwidth=5,  text='first 2 lines '
     ,relief="sunken", width=200, height=100)
   

    content.grid(column=0, row=0, sticky=(N, S, E, W))
   
    frame.grid(column=2, row=0, columnspan=1, rowspan=nb_fields+1,
              sticky=(N, S, E, W))

    #text of file
    fw_label = ttk.tkinter.Text(frame ,bd =1)
    fw_label.pack(side =LEFT, expand =YES, fill =BOTH)     
    scroll = ttk.Scrollbar(frame,   command = fw_label.yview)
    scroll.pack(side =RIGHT, fill =Y)
    fw_label.configure(yscrollcommand = scroll.set)
    fw_label.insert(END, line1 +'\n'+ line2)
    #fw_label.config(state=DISABLED)
   
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
   
    # Resize rules
    top.columnconfigure(0, weight=1)
    top.rowconfigure(0, weight=1)
    #grid widgets
    content.grid( column=0, row=0,sticky=(N,W,S,E))
    top.grab_set()

def t_doubleClicked(event):
    "action on dbl_click on the Database structure" 
    selitems = db_tree.selection()
    if selitems:
        selitem = selitems[0]
        #item_id = db_tree.focus()
        text = db_tree.item(selitem, "text")
        instruction = db_tree.item(selitem, "values")[0]
        #parent Table
        parent_node =  db_tree.parent(selitem)
        parent_table = db_tree.item(parent_node, "text")
        #create a new tab 
        new_tab_ref = n.new_query_tab(parent_table, instruction)
        try :
            cur = conn.execute(instruction)
            my_curdescription=cur.description
            rows = cur.fetchall()
            #A query may have no result(like for an "update", or a "fail")
            if    cur.description != None :
                rowtitles = [row_info[0] for row_info in cur.description]
                #add result
                n.add_treeview(new_tab_ref, rowtitles, rows)
        except:
            pass #show nothing
        
def actualize_db():
    "re-build database view"

    #bind double-click
    db_tree.tag_bind('ttk', '<Double-1>', t_doubleClicked)
    #t.delete(database_file)
    try :
        db_tree.delete("Database")
    except :
        pass
    id0 = db_tree.insert("",0,"Database",
                   text=(database_file.replace("\\","/")).split("/")[-1] , 
                   values=(database_file)   )

    #add the master
    add_things(id0,'master_table', """
     SELECT 'sqlite_master', 'sqlite_master', '--no def.' """)
    
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
    

def quit_db():
   """quit application button"""
   global tk_win 
   messagebox.askyesno(
	   message='Are you sure you want to quit ?',
	   icon='question', title='Install')
   messagebox.showinfo(message='Have a good day')
   tk_win.destroy()
#F/menu actions

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

    global tk_win
    # create a tkk graphic interface
    # with menu, toolbar, left 'Database' Frame, right 'Queries' Notebook 

    #create main window tk_win
    tk_win = Tk()
    tk_win.title('Sqlite_py_manager : browsing SQLite datas on the go')
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
                           
    menu_help.add_command(label='about',command = lambda : messagebox.showinfo(
       message="""Sqlite_py_manager is a small SQLite Browser written in Python
            \n(https://github.com/stonebig/baresql/blob/master/examples)"""))

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

    #add new_tab_button
    Button(toolbar, image = tk_icon['newtab_img'] ,
            command=new_tab).pack(side=LEFT, padx=2, pady=2)

    #create a paned window 'p' that contains 2 frames : 'Database', 'Queries'
    # 'p' layout is managed by pack()
    p  = ttk.Panedwindow(tk_win, orient=HORIZONTAL)
    p.pack(fill=BOTH, expand=1)

    f_database = ttk.Labelframe(p, text='Databases', width=200 , height=100)
    p.add(f_database)

    f_queries = ttk.Labelframe(p, text='Queries', width=200, height=100)
    p.add(f_queries)
    
    #build tree view 't' inside the left 'Database' Frame
    db_tree = ttk.Treeview(f_database , displaycolumns = [], 
                           columns = ("detail"))

    #create a  notebook 'n' inside the right 'Queries' Frame
    n = notebook_for_queries(f_queries , [])

    db_tree.tag_configure("ttk")
    db_tree.pack(fill = BOTH , expand = 1)
 
    #Start with a memory Database
    new_db_mem()
    
    #Propose a Demo
    welcome_text = """-- Welcome Frame = a small memo (demo = click on "->")
\n-- to CREATE a table  :
create table items  (ItemNo, Description,Kg);
create table products(ItemNo TEXT PRIMARY KEY,Description TEXT ,Kg NUMERIC);
\n-- to CREATE an index :
CREATE INDEX items_id1 ON items(ItemNo ASC, Kg Desc);
\n-- to CREATE a view :
CREATE VIEW items_and_product as select * 
   from items as i inner join products as p ON i.ItemNo=p.ItemNo;
\n-- to CREATE a Python embedded function :
pydef mysqrt(s):
    return ("%s" %s**.5);
\n-- to USE a python embedded function :
select mysqrt(3), sqlite_version();"""
    n.new_query_tab("Welcome", welcome_text )
    
    tk_win.mainloop()

