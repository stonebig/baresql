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

class App: 
    "the GUI graphic application"
    def __init__(self):
        "create a tkk graphic interface with a main window tk_win"

        self.conn_inst={}        
        self.database_file = ""
        self.tk_win = Tk()
        self.tk_win.title('A graphic SQLite Client in 1 Python file')
        self.tk_win.option_add('*tearOff', FALSE) # tk documentation recommands 
        self.tk_win.minsize(600,200)              # minimal size
    
        #With a Menubar and Toolbar
        self.create_menu()
        self.create_toolbar()

        #With a Panedwindow of two frames: 'Database' and 'Queries'
        p  = ttk.Panedwindow(self.tk_win, orient=HORIZONTAL)
        p.pack(fill=BOTH, expand=1)

        f_database = ttk.Labelframe(p, text='Databases', width=200, height=100)
        p.add(f_database)
        f_queries = ttk.Labelframe(p, text='Queries', width=200, height=100)
        p.add(f_queries)
    
        #build tree view 't' inside the left 'Database' Frame
        self.db_tree = ttk.Treeview(f_database , displaycolumns = [], 
                           columns = ("detail","action"))
        self.db_tree.tag_configure("run")
        self.db_tree.pack(fill = BOTH , expand = 1)

        #create a  notebook 'n' inside the right 'Queries' Frame
        self.n = notebook_for_queries(self.tk_win, f_queries , [])

    def create_menu(self):
        menubar = Menu(self.tk_win)
        self.tk_win['menu'] = menubar
    
        #feeding the top level menu
        self.menu = Menu(menubar)
        menubar.add_cascade(menu=self.menu, label='Database')

        self.menu_help = Menu(menubar)
        menubar.add_cascade(menu=self.menu_help, label='?')

        #feeding database sub-menu
        self.menu.add_command(label = 'New Database', command = self.new_db)
        self.menu.add_command(label ='New In-Memory Database', command = 
                          lambda : self.new_db(":memory:"))
        self.menu.add_command(label = 'Connect to Database ...', 
                              command = self.open_db)
        self.menu.add_command(label = 'Close Database', command= self.close_db)   
        self.menu.add_separator()
        self.menu.add_command(label= 'Attach Database',command= self.attach_db)   
        self.menu.add_separator()
        self.menu.add_command(label = 'Quit', command = self.quit_db)   
                          
        self.menu_help.add_command(label='about',
            command = lambda : messagebox.showinfo( message=
            """Sqlite_py_manager : a graphic SQLite Client in 1 Python file
            \n(version 2014-05-24a 'Assassination of Class Room')
            \n(https://github.com/stonebig/baresql/blob/master/examples)""")) 


    def create_toolbar(self):
        "Toolbar of the application"
        self.toolbar = Frame(self.tk_win, relief=RAISED)
        self.toolbar.pack(side=TOP, fill=X)
        self.tk_icon = self.get_tk_icons()
    
        #list of image, action, tootip :
        to_show=[('refresh_img', self.actualize_db, "Actualize Databases")
           ,('run_img', self.run_tab, "Run Script Selection")
           ,('deltab_img', lambda x=self: x.n.del_tab(), "Delete current tab")
           ,('deltabresult_img',  lambda x=self:
               x.n.remove_treeviews(x.n.notebook.select()), "Clear tab Result")
           ,('newtab_img', lambda x=self:
               x.n.new_query_tab("___",""), "Create a New Tab")
           ,('csvin_img', lambda x=self: import_csvtb([x.conn,x.actualize_db]),
                     "Import a CSV file into a Table")
           ,('csvex_img', lambda x=self: export_csvtb([x.conn, x.db_tree]),
                     "Export Selected Table to a CSV file")
           ,('qryex_img', lambda x=self: export_csvqr([x.conn, x.n]),
                     "Export Selected Query to a CSV file")]
    
        for img, action, tip in to_show:
            b = Button(self.toolbar, image= self.tk_icon[img], command= action)
            b.pack(side=LEFT, padx=2, pady=2)
            self.createToolTip(b, tip)

    
    def new_db(self, filename = ''):
        """create a new database"""
        if filename == '':
            filename = filedialog.asksaveasfilename(defaultextension='.db',
                title="Define a new database name and location",                          
                filetypes=[("default","*.db"),("other","*.db*"),("all","*.*")])

        if filename != '':
            self.database_file =  filename 
            self.conn = sqlite.connect(self.database_file,
                   detect_types = sqlite.PARSE_DECLTYPES)
            self.actualize_db()


    def open_db(self):
       """open an existing database"""
       filename = filedialog.askopenfilename(defaultextension='.db',
              filetypes=[("default","*.db"),("other","*.db*"),("all","*.*")])

       if filename != "(none)":
           self.database_file =  filename 
           self.conn = sqlite.connect(self.database_file,
                   detect_types = sqlite.PARSE_DECLTYPES)
           self.actualize_db()
       
       
    def attach_db(self):
       """attach an existing database"""
       filename = filedialog.askopenfilename(defaultextension='.db',
              title="Choose a database to attach ",    
              filetypes=[("default","*.db"),("other","*.db*"),("all","*.*")])
       attach = ((filename.replace("\\","/")).split("/")[-1]).split(".")[0]

       if filename != '':
           attach_order = "ATTACH DATABASE '%s' as '%s' "%(filename,attach);
           cur = self.conn.execute(attach_order)
           cur.close
           self.actualize_db()

    def close_db(self):
       """close database"""
       try :
           self.db_tree.delete("Database")
       except :
           pass
       self.conn.close
   

    def actualize_db(self):
        "re-build database view"
        #bind double-click for easy user interaction
        self.db_tree.tag_bind('run', '<Double-1>', self.t_doubleClicked)
        self.db_tree.tag_bind('run_up', '<Double-1>', self.t_doubleClicked)
    
        #delete existing tree entries before re-creating them
        for node  in self.db_tree.get_children():
            self.db_tree.delete(node )

        #create initial node
        id0 = self.db_tree.insert("",0,"Database",
                 text = (self.database_file.replace("\\","/")).split("/")[-1] , 
                 values = (self.database_file,"")   )

        #add master_table, Tables, Views, Trigger, Index
        for category in ['master_table', 'table', 'view', 'trigger', 'index',
        'pydef']:
            self.add_thingsnew( id0, category)

        #redo for attached databases
        for att_db in self.add_thingsnew(id0,'attached_databases' ):
            #create initial node for attached table
            id0 = self.db_tree.insert("",'end', att_db + "(Attached)",
                text = att_db + " (attached database)", values = (att_db,"") )
                
            #add attached db's master_table, Tables, Views, Trigger, and Index  
            for categ in ['master_table', 'table', 'view', 'trigger', 'index']:
                self.add_thingsnew( id0, categ, att_db +".")


    def quit_db(self):
       """quit application button"""
       messagebox.askyesno(
	       message='Are you sure you want to quit ?',
	       icon='question', title='Install')
       self.tk_win.destroy()


    def run_tab(self):
       """clear previous results and run current script of a tab"""
       active_tab_id = self.n.notebook.select()
       if active_tab_id != '':
           #remove previous results
           self.n.remove_treeviews(active_tab_id)
           #get current selection (or all)
           fw =self.n.fw_labels[active_tab_id]
           script = ""
           try :
               script = (fw.get('sel.first', 'sel.last')) 
           except:
               script = fw.get(1.0,END)[:-1]   

           self.create_and_add_results(script, active_tab_id)
           #workaround bug http://bugs.python.org/issue17511 
           #otherwise the focus is still set but not shown (for python <=3.3.2)
           fw.focus_set()

              
    def t_doubleClicked(self, event):
        "action on dbl_click on the Database structure" 
        #determine item to consider   
        selitem = self.db_tree.focus() #the item having the focus  
        seltag = self.db_tree.item(selitem,"tag")[0]  
        if seltag == "run_up" : # if 'run-up' tag do as if dbl-click 1 level up 
            selitem =  self.db_tree.parent(selitem)
        #get final information : text, selection and action   
        definition , action = self.db_tree.item(selitem, "values")
        tab_text = self.db_tree.item(selitem, "text")
        script = action + " limit 999 " if action !="" else definition

        #create a new tab and run it if action suggest it
        new_tab_ref = self.n.new_query_tab(tab_text, script)
        if action != "": #run the new_tab created
           self.run_tab()          


    def get_tk_icons(self):
        "retuns a dictionary of {iconname : icon_in_tk_format} from B64 images"

        #to create this base 64 from a toto.gif image of 24x24 size do :
        #    import base64
        #    b64 = base64.encodestring(open(r"toto.gif","rb").read())
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
'''
        ,'csvin_img':'''\
R0lGODdhGAAYAJkAAP///wAAADOqMwAAACwAAAAAGAAYAAACVYQPoZobeR4yEtZ3J511e845zah1
oKV9WEQxqYOJX0rX9iHkd50LO+Iz9H5A35CI6wWRwiOz6WQqdU8mrLGYlVgZSM3UNYWyYeKKJEZk
rl4aOxLLTgoAOw==
'''
        ,'csvex_img':'''\
R0lGODdhGAAYAJkAAP///wAAADOqMwAAACwAAAAAGAAYAAACVYQPoZobeR4yEtZ3J511e845zah1
oKV9WEQxqYOJX0rXtoDndp3jO6/7aXoC4UTnMxqCgKKSqVwmo9TWonGF1DIZLc3UNYWuYeOKJEZw
ZemIzI11IQoAOw==
'''
        ,'qryex_img':'''\
R0lGODdhGAAYAJkAAP///wAAADNm/zOqMywAAAAAGAAYAAACXIQPoZobeR4yEtZ3J511e845zah1
oKV9WEQxqYOJX0rX9oDndp3jO6/7aXoD4UTnMxqCgKKSqVwmo9SD4GrFGq4CGvbbBQO03m4WQZ5w
s+ZxWt12o+PVX/pORxQAADs=
'''
      }   
        #transform 'in place' base64 icons into tk_icons 
        for key, value in icons.items():
            icons[key] = ttk.tkinter.PhotoImage(data = value)
        return  icons
 
   
    def createToolTip(self, widget, text ):
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
        widget.bind( "<Leave>", close )


    def add_thingsnew(self, root_id , what , attached_db = ""): 
        "add a sub-tree to database tree pan"
        tables = get_things(self.conn, self.conn_inst,root_id, what, attached_db) 
        #level 1 : create  the "what" node (as not empty)
        if len(tables)>0:
            idt = self.db_tree.insert(root_id,"end", "%s%s" % (attached_db, what)
                   , text="%s (%s)" % (what, len(tables)) , values=("","") )  

            #Level 2 : print object creation, and '(Definition)' if Table/View
            for tab in tables:
                definition = tab[2] ; sql3 = ""
                if tab[3] != '':
                    #it's a table : prepare a Query with names of each column
                    colnames = [col[1] for col in tab[3]]
                    columns = [col[0] for col in tab[3]]
                    sql3 = "select ["+"] , [".join(colnames)+"] from " + (
                            "%s[%s]"% (attached_db,tab[1])  )
                idc = self.db_tree.insert(idt,"end",  "%s%s" % (attached_db,tab[0]) 
                     ,text=tab[1],tags=('run',) , values=(definition,sql3))                    
                if sql3 != "":
                    self.db_tree.insert(idc,"end",("%s%s.%s"% (attached_db,tab[1], -1)),
                    text = ['(Definition)'],tags=('run',), values=(definition,""))
                    #level 3 : Insert a line per column of the Table/View
                    for c in range(len(columns)):
                        self.db_tree.insert(idc,"end",
                           ("%s%s.%s" % (attached_db, tab[1], c)),
                           text = columns[c], tags = ('run_up',), values = ('',''))
        return [i[1] for i in tables]


    def create_and_add_results(self, instructions, tab_tk_id):
        """execute instructions and add them to given tab results"""
        jouer = baresql()
        a_jouer = jouer.get_sqlsplit(instructions, remove_comments = True) 
        for instruction in a_jouer:
            instruction = instruction.replace(";","").strip(' \t\n\r')
            rows=[] ; first_line = instruction.splitlines()[0]
            rowtitles=("#N/A",); Tab_Title = "Qry"
            if instruction[:5] == "pydef" :
                instruction = instruction.strip('; \t\n\r')
                Tab_Title = "Info"
                exec(instruction[2:]  , globals() , locals())
                firstline=(instruction[5:].splitlines()[0]).lstrip()
                firstline = firstline.replace(" ","") + "(" 
                instr_name=firstline.split("(",1)[0].strip()
                instr_parms=firstline.count(',')+1
                instr_add = "self.conn.create_function('%s', %s, %s)" %(
                   instr_name,instr_parms, instr_name)

                exec(instr_add , globals() , locals())
                rowtitles=("Creating embedded python function",)
                for i in (instruction[2:].splitlines()) :
                   rows.append((i,))             
                rows.append((instr_add,))

                #manual housekeeping
                if not self.conn in self.conn_inst :
                    self.conn_inst[self.conn] = {}
                conn_def = self.conn_inst[self.conn]
                try:    
                     the_help= dict(globals(),**locals())[instr_name].__doc__
                     conn_def[instr_name]={'parameters':instr_parms,
                                       'help':the_help, 'pydef':instruction}
                except:
                    pass
            elif instruction != "":
              try :
                  cur = self.conn.execute(instruction)
                  rows = cur.fetchall()
                  #A query may have no result( like for an "update")
                  if    cur.description != None :
                      rowtitles = [row_info[0] for row_info in cur.description]
                  cur.close
              except sqlite.Error as msg:#OperationalError
                  rowtitles=('Error !',)
                  rows=[(msg,)]
                  self.n.add_treeview(tab_tk_id, rowtitles, rows,
                  "Error !", first_line )
                  break
            #end of one sql
            if rowtitles != ("#N/A",) :#rows!=[]  :
                self.n.add_treeview(tab_tk_id, rowtitles, rows, 
                                    Tab_Title, first_line)


class notebook_for_queries():
    """Create a Notebook with a list in the First frame
       and query results in following treeview frames """
    def __init__(self, tk_win , root, queries):
        self.tk_win=tk_win
        self.root = root
        self.notebook = Notebook(root) #ttk.
        
        self.fw_labels = {} # tab_tk_id -> Scripting frame python object
        self.fw_result_nbs = {} # tab_tk_id -> Notebook of Results
        
        # Resize rules
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        #grid widgets
        self.notebook.grid(row=0, column=0, sticky=(N,W,S,E))


    def new_query_tab(self, title, query ):
        "add a new Tab 'title' to the notebook, containing the Script 'query'"

        fw_welcome = ttk.Panedwindow(self.tk_win, orient=VERTICAL)   #tk_win   
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
        
        #keep tab reference to script (by tk id)
        self.fw_labels[working_tab_id]  = fw_label        

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


    def del_tab(self):
       """delete active notebook tab's results"""
       given_tk_id = self.notebook.select()
       if given_tk_id !='':
           self.notebook.forget(given_tk_id)


    def remove_treeviews(self, given_tk_id  ):
        "remove results from given tab tk_id"
        if given_tk_id !='':
            myz  =  self.fw_result_nbs[given_tk_id]
            for xx in list(myz.children.values()):
                xx.grid_forget() ; xx.destroy()

        
    def add_treeview(self, given_tk_id,  columns, data, title = "__", subt=""):
        "add a dataset result to the given tab tk_id"
        #Ensure we work on lists
        tree_columns = [columns] if type(columns)==type('e') else columns
        lines = [data] if type(data)==type('e') else data

        #Get back reference to Notebooks of Results
        #(see http://www.astro.washington.edu/users/rowen/TkinterSummary.html)
        fw_result_nb  =  self.fw_result_nbs[given_tk_id]           

        #Create a Labelframe to contain new resultset and scrollbars 
        f2 = ttk.Labelframe(fw_result_nb, 
            text=('(%s lines) %s' % (len(lines),subt)), width=200, height=100) 
        f2.pack(fill = 'both', expand=True)
        fw_result_nb.add(f2 , text = title)

        #lines=queries
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
                command=lambda c=col: self.sortby(fw_Box, c, 0))
            fw_Box.column(col, width=font.Font().measure(col.title()))

        #feed Treeview Lines
        for items in lines:
            # if line is a string, redo a tuple
            item = (items,) if type(items)==type('ee') else items

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

    def sortby(self, tree, col, descending):
        """Sort a ttk treeview contents when a column is clicked on."""
        # grab values to sort
        data = [(tree.set(child, col), child) for child in tree.get_children()]

        # reorder data
        data.sort(reverse=descending)
        for indx, item in enumerate(data):
            tree.move(item[1], '', indx)

        # switch the heading so that it will sort in the opposite direction
        tree.heading(col, command=lambda col=col: 
                                 self.sortby(tree, col, int(not descending)))
    

def guess_sql_creation(table_name, separ, decim, header, data_is, quoter='"'):
    "guessing sql creation request"
    dlines = list(csv.reader(data_is.replace('\n\n','\n').splitlines()
            ,delimiter = separ, quotechar = quoter))
    r , typ = list(dlines[0]) , list(dlines[1]) 
    for i in range(len(r)):
        try:
            float (typ[i].replace(decim,'.'))
            typ[i] = 'REAL'
        except:
            typ[i] = 'TEXT'
    if header:
        head = ",\n".join([('[%s] %s'%(r[i],typ[i])) for i in range(len(r))])
        sql_crea = ("CREATE TABLE [%s] (%s);"  % (table_name, head))
    else:
        head = ",".join(["c_"+("000" +str(i))[-3:] for i in range(len(r))])
        sql_crea = ("CREATE TABLE [%s] (%s);"  % (table_name, head))
    return sql_crea, typ   , head                 

def import_csvtb_ok(thetop, entries, actions):
    "read input values from tk formular"
    conn  , actualize_db = actions
    #build dico of result
    d={}
    for f in entries:
        if type(f)!= type('e'):
            d[f[0]]= f[1]()
    #affect to variables
    csv_file = d['csv Name'].strip()
    table_name = d['table Name'].strip()
    separ = d['column separator'] ; decim = d['Decimal separator']
    header = d['Header line'] ; creation = d['Create table']
    replacing = d['Replace existing data'] ; encoding_is = d['Encoding']
    data = d["first 3 lines"]  ; quotechar = d['string delimiter']
    do_manu = d['use manual creation request'] ; manu = d["creation request"]
    #Action
    if   csv_file != "(none)" and len(csv_file)*len(table_name)*len(separ)>1:
        thetop.destroy()
        curs = conn.cursor()
        #Do initialization job
        sql, typ, head = guess_sql_creation(table_name, separ, decim,
                                            header, data, quotechar)
        if creation:
            curs.execute("drop TABLE if exists [%s];" % table_name)
            if do_manu:
                sql = ("CREATE TABLE [%s] (%s);"  % (table_name, manu))
                print(sql)
            curs.execute(sql )
        if replacing:
            curs.execute("delete from [%s];" % table_name)
        sql="INSERT INTO [%s]  VALUES(%s);" % (
               table_name,  ", ".join(["?"]*len(typ)))

        reader = csv.reader(open(csv_file, 'r', encoding = encoding_is),
                           delimiter = separ, quotechar='"')
        #read first_line if needed to skip headers 
        if header:
            row = next(reader)
        if decim != "." : # one by one needed
            for row in reader:
               if type(row) !=type ("e"):
                   for i in range(len(row)): 
                       row[i] = row[i].replace( decim,  ".") 
               curs.execute(sql, row)
        else :
            curs.executemany(sql, reader)
        conn.commit()
        actualize_db()

     
def create_dialog(title, fields_in, buttons, actions ):
    "create a formular with title, fields, button, data"
    #Drawing the request form 
    top = Toplevel()
    top.title(title)
    top.columnconfigure(0, weight=1)
    top.rowconfigure(0, weight=1)
    #drawing global frame
    content = ttk.Frame(top)
    content.grid(column = 0, row = 0, sticky = (N, S, E, W))
    content.columnconfigure(0, weight=1)
    #fields = Horizontal FrameLabel, or
    #         label, default_value, 'r' or 'w' default_width,default_height
    fields = fields_in ; mf_col = -1 
    for f in range(len(fields)): #same structure out
        field = fields[f]
        if type(field) == type('e') or mf_col == -1:# A new horizontal frame           
            mf_col += 1 ; ta_col = -1
            if type(field) == type('e') and field == '' :
                mf_frame = ttk.Frame(content, borderwidth = 1) 
            else:
                mf_frame = ttk.LabelFrame(content,borderwidth=1, text=field)
            mf_frame.grid(column = 0, row = mf_col, sticky ='nsew')
            Grid.rowconfigure(mf_frame, 0, weight=1)
            content.rowconfigure(mf_col, weight=1)
        if type(field) != type('e'): #A New Vertical Frame
            ta_col += 1
            Grid.columnconfigure(mf_frame, ta_col,weight=1);
            packing_frame = ttk.Frame(mf_frame, borderwidth = 1)
            packing_frame.grid(column = ta_col, row = 0 , sticky ='nsew')
            Grid.columnconfigure(packing_frame, 0, weight=1)
            #prepare width and height and writable status
            width = field[3] if len(field)>3 else 30 
            height = field[4] if len(field)>4 else 30 
            status = "normal"
            if len(field)>=3 and field[2] == "r":
                   status = "disabled"
            #switch between object types
            if len(field)>4:
                #datas
                d_frame = ttk.LabelFrame(packing_frame, borderwidth = 5
                       , width=width , height=height   , text= field[0]  )
                d_frame.grid(column= 0, row= 0, sticky ='nsew', pady=1, padx=1)
                Grid.rowconfigure(packing_frame, 0, weight=1)
                fw_label = ttk.tkinter.Text(d_frame, bd=1,
                                            width=width, height=height)
                fw_label.pack(side= LEFT, expand= YES, fill= BOTH)     
                scroll = ttk.Scrollbar(d_frame, command = fw_label.yview)
                scroll.pack(side = RIGHT, expand = NO, fill = Y)
                fw_label.configure(yscrollcommand = scroll.set)
                fw_label.insert(END, ("%s" %field[1]))
                fw_label.configure( state = status)
                Grid.rowconfigure(d_frame, 0, weight=1)
                Grid.columnconfigure(d_frame, 0, weight=1)
                #Data Text Extractor in the fields list ()
                #see stackoverflow.com/questions/17677649 (loop and lambda)
                fields[f][1] = lambda x=fw_label : x.get('1.0','end')
            elif field[1]==True or field[1]==False:
                #Boolean Field
                name_var = BooleanVar()
                name = ttk.Checkbutton(packing_frame, text=field[0], 
                           variable = name_var, onvalue=True, state = status)
                name_var.set(field[1])  
                name.grid(column = 0, row = 0, sticky ='nsew', pady=5, padx=5)
                fields[f][1] =  name_var.get 
            else : #Text
                namelbl = ttk.Label(packing_frame,   text=field[0] )
                namelbl.grid(column=0, row=0, sticky='nsw', pady=5, padx=5)
                name_var = StringVar()
                name = ttk.Entry(packing_frame, textvariable = name_var,
                                 width=width, state = status)
                name_var.set(field[1])
                name.grid(column=1, row=0,   sticky='nsw', pady=0, padx=10)
                fields[f][1] = name_var.get 
    # Adding button below the same way
    mf_col += 1
    packing_frame = ttk.LabelFrame(content, borderwidth = 5  )
    packing_frame.grid(column = 0, row = mf_col, sticky ='nsew')
    okbutton = ttk.Button(packing_frame, text = buttons[0], 
       command = lambda  a = top, b = fields, c = actions: (buttons[1])(a,b,c)) 
    cancelbutton = ttk.Button(packing_frame, text = "Cancel",
            command = top.destroy)
    okbutton.grid(column=0, row=mf_col)
    cancelbutton.grid(column=1, row=mf_col)
    for x in range(3):
        Grid.columnconfigure(packing_frame, x,weight=1)
    top.grab_set()

def import_csvtb(actions):
    """import csv dialog (with guessing of encoding and separator)"""
    csv_file = filedialog.askopenfilename(defaultextension='.db',
              title="Choose a csv file (with header) to import ",
              filetypes=[("default","*.csv"),("other","*.txt"),("all","*.*")])

    #Guess encoding
    with open(csv_file, "rb") as f:
        data = f.read(5)
    if data.startswith(b"\xEF\xBB\xBF"): # UTF-8 with a "BOM"
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
        has_header = True ; default_sep=","  ; default_quote='"'  
    try:
        dialect = csv.Sniffer().sniff(preview)
        has_header = csv.Sniffer().has_header(preview)
        default_sep = dialect.delimiter
        default_quote = Dialect.quotechar
    except: #sniffer can fail
        pass
    default_decim = "." if default_sep != ";" else ","
        
    #Request form : List of Horizontal Frame names 'FramLabel' 
    #    or fields :  'Label', 'InitialValue',['r' or 'w', Width, Height]
    table_name = (csv_file.replace("\\","/")).split("/")[-1].split(".")[0]
    dlines = "\n\n".join(preview.splitlines()[:3])
    guess_who = guess_sql_creation(table_name,
           default_sep, default_decim, has_header, dlines, default_quote)[2]
    fields_in = ['',[ 'csv Name', csv_file , 'r', 100],''
     ,['table Name', table_name]
     ,['column separator', default_sep, 'w', 20]
     ,['string delimiter', default_quote, 'w', 20]
     ,'',['Decimal separator', default_decim]
     ,['Encoding', encodings[0] ]
     ,'Fliflaps',['Header line', has_header]
     ,['Create table', True  ]
     ,['Replace existing data', True] ,''
     ,['first 3 lines' , dlines,'r', 100,10] ,''
     ,['use manual creation request', False],''
     ,['creation request', guess_who,'w', 100,10]   ]
 
    create_dialog(("Importing %s" % csv_file ), fields_in  
                  , ("Import", import_csvtb_ok), actions )  


def export_csv_ok(thetop, entries, actions):
    "export a csv table (action)"
    conn = actions[0]
    import csv
    #build dico of result
    d={}
    for f in entries:
        if type(f)!= type('e'):
            d[f[0]]= f[1]()
    csv_file=d['csv Name'].strip() ; separ = d['column separator']
    header = d['Header line'] ; encoding_is = d['Encoding']
    query_is = d["Data to export (MUST be 1 Request)"]
    cursor = conn.cursor()
    cursor.execute(query_is)
    thetop.destroy()
    with open(csv_file, 'w', newline = '', encoding = encoding_is) as fout:
        writer = csv.writer(fout, delimiter = separ,
                            quotechar='"', quoting=csv.QUOTE_MINIMAL)
        if header:
            writer.writerow([i[0] for i in cursor.description]) # heading row
        writer.writerows(cursor.fetchall())

    
def export_csv_dialog(query = "select 42", text="undefined.csv", actions=[]):
    "export csv dialog"
    #Proposed encoding (we favorize utf-8 or utf-8-sig)
    encodings = ["utf-8",locale.getdefaultlocale()[1],"utf-16","utf-8-sig"]
    if os.name == 'nt': 
        encodings = ["utf-8-sig",locale.getdefaultlocale()[1],"utf-16","utf-8"]
    #Proposed csv separator
    default_sep=[",",";"]

    file_tk = filedialog.asksaveasfile(mode='w',defaultextension='.db',
              title = text,                          
              filetypes=[("default","*.csv"),("other","*.txt"),("all","*.*")])
    csv_file = file_tk.name
    file_tk.close
    if csv_file != "(none)":
        #Request form (http://www.python-course.eu/tkinter_entry_widgets.php)
        fields = ['',['csv Name', csv_file,'w',100 ],''
           ,['column separator',default_sep[0]]
           ,['Header line',True]
           ,['Encoding',encodings[0]], ''
           ,["Data to export (MUST be 1 Request)" ,(query), 'w', 100,10] ] 
 
        create_dialog(("Export to %s" % csv_file), fields ,
                  ("Export",  export_csv_ok) , actions)


def export_csvtb( actions):
    "get table selected definition and launch cvs export dialog"
    #determine item to consider   
    db_tree = actions[1]
    selitem = db_tree.focus() #the item having the focus  
    if selitem !='':
        seltag = db_tree.item(selitem,"tag")[0] 
        if seltag == "run_up" : # if 'run-up', do as if dbl-click 1 level up 
            selitem =  db_tree.parent(selitem)
        #get final information 
        definition , query = db_tree.item(selitem, "values")
        title = ("Export Table [%s] to ?" %db_tree.item(selitem, "text"))
        if query != "": #run the export_csv dialog
            export_csv_dialog(query, title, actions )   

              
def export_csvqr( actions):
    "get tab selected definition and launch cvs export dialog"
    n= actions[1]
    active_tab_id = n.notebook.select()
    if active_tab_id !='': #get current selection (or all)
        fw =n.fw_labels[active_tab_id]
        action = ""
        try :
            query = fw.get('sel.first', 'sel.last')
        except:
            query = fw.get(1.0,END)[:-1]   
        if query != "":
            export_csv_dialog(query , "Export Query", actions)   

    
def get_things(conn, conn_inst, root_id , what , attached_db = "", tbl =""):
    "database objects of 'what': [objectCode, objectName, Definition,[Lvl -1]]"
    #dico = what : what qry, result id, result text, result crea, 'what' below 
    #    or what : other 'what' specification to use in thi dictionnary
    dico={'index': 'trigger',
          'trigger': ("""select '{0:s}' || name, name, sql FROM 
                     {0:s}sqlite_master WHERE type='{1:s}' order by name""",
                     '{0:s}','{1:s}','{2:s}',''),
          'master_table': ("select '{0:s}sqlite_master','sqlite_master'",
                     '{0:s}','{1:s}','--auto-created','fields'),
          'table': 'view',
          'view': ("""select '{0:s}' || name, name, sql FROM {0:s}sqlite_master 
                     WHERE type='{1:s}' order by name""",
                     '{0:s}','{1:s}','{2:s}','fields'),
          'fields': ("pragma {0:s}table_info([{2:s}])", 
                     '{1:s} {2:s}','{1:s}', '',''),
          'attached_databases': ("PRAGMA database_list",
                     '{1:s}','{1:s}', "ATTACH DATABASE '{2:s}' as '{1:s}'",''),
          'pydef': ("#N/A", '{0:s}','{0:s}','{1:s}', '')
          }
    order = dico[what] if type(dico[what]) != type('e') else dico[dico[what]] 
    Tables = []
    if what == "pydef": #pydef request is not sql
        try :
            resu = [[k , v['pydef']] for k, v in conn_inst[conn].items()]
        except:       
            resu = []
    else:
        #others are sql request
        resu = conn.execute(order[0].format(attached_db,what,tbl)).fetchall()
        #result must be transformed in a list, and attached db 'main' removed
        resu = list(resu) if what != 'attached_databases' else list(resu)[1:]
    #generate tree list for this 'what' category level :
    #     [objectCode, objectName, Definition, [Level below] or '']
    for rec in resu:
        result = [order[i].format(*rec) for i in range(1,5)]
        if result[3] != '':
            resu2 = get_things(conn, conn_inst, root_id , result[3] ,
                               attached_db , result[1])
            result[3] = resu2
        Tables.append(result)
    return Tables    


class baresql():
    "a tiny sql tokenizer"
    def __init__(self, connection="sqlite://", keep_log = False,
                 cte_inline = True):
        nothing_to_see = 1
 
    def get_token(self, sql, start = 0):
        "return next token type and ending+1 from given sql start position"
        length = len(sql) ; 
        i = start ; token = 'TK_OTHER'
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
        

if __name__ == '__main__':
    # create a tkk graphic interface with a main window tk_win
    app=App()

    #Start with a memory Database and a welcome
    app.new_db(":memory:")
    welcome_text = """-- SQLite Memo (Demo = click on green "->" and "@" icons)
\n-- to CREATE a table 'items' and a table 'parts' :
create table item (ItemNo, Description,Kg  , PRIMARY KEY (ItemNo));
create table part(ParentNo, ChildNo , Description TEXT , Qty_per REAL);
\n-- to CREATE an index :
CREATE INDEX parts_id1 ON part(ParentNo Asc, ChildNo Desc);
-- to CREATE a view 'v1':
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
\n-- to EXPORT :
--    a TABLE, select TABLE, then click on icon 'SQL->CSV'
--    a QUERY RESULT, select the SCRIPT text, then click on icon '???->CSV', 
-- example : select the end of this line: SELECT SQLITE_VERSION()  """
    app.n.new_query_tab("Welcome", welcome_text )
    
    app.tk_win.mainloop()

