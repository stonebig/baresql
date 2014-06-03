#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals, division #Python2.7

import sqlite3 as sqlite 
import sys, os, locale, csv , io , codecs

try: #We are Python 3.3+
    from tkinter import * 
    from tkinter import font, ttk, filedialog, messagebox
    from tkinter.ttk import *
except: #or we are Python2.7
    from Tkinter import *  
    import Tkinter as tkinter, tkFont as font
    import tkFileDialog as filedialog, tkMessageBox as messagebox  
    from ttk import *
    import ttk as ttk

class App: 
    "the GUI graphic application"
    def __init__(self):
        "create a tkk graphic interface with a main window tk_win"
        self.conn = None #baresql database object
        self.database_file = ""
        self.tk_win = Tk()
        self.tk_win.title('A graphic SQLite Client in 1 Python file')
        self.tk_win.option_add('*tearOff', FALSE) # tk documentation recommands 
        self.tk_win.minsize(600,200)              # minimal size
    
        self.font_size = 10
        self.font_wheight = 0
        #self.chg_size()
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
            \n(version 2014-06-03a 'See me now ?')
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
           ,('dbdef_img', self.savdb_script,"Save Database as a SQL Script")
           ,('qryex_img', lambda x=self: export_csvqr([x.conn, x.n]),
                     "Export Selected Query to a CSV file") 
           ,('sqlin_img', self.load_script , "Load a SQL Script File") 
           ,('sqlsav_img', self.sav_script,"Save a SQL Script in a File") 
           ,('chgsz_img', self.chg_size,"Modify Font Size")]
    
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
            self.conn = baresql(self.database_file)
            self.actualize_db()


    def open_db(self):
       """open an existing database"""
       filename = filedialog.askopenfilename(defaultextension='.db',
              filetypes=[("default","*.db"),("other","*.db*"),("all","*.*")])
       if filename != "(none)":
           self.database_file =  filename 
           self.conn = baresql(self.database_file)
           self.actualize_db()
       
       
    def load_script(self):
       """load a script file"""
       filename = filedialog.askopenfilename(defaultextension='.sql',
              filetypes=[("default","*.sql"),("other","*.txt"),("all","*.*")])
       if filename != "":
           text = ((filename.replace("\\","/")).split("/")[-1]).split(".")[0]
           with io.open(filename, encoding = Guess_encoding(filename)[0]) as f:
               new_tab_ref = self.n.new_query_tab(text, f.read())

    def savdb_script(self):
       """save database as a script file"""
       filename = filedialog.asksaveasfilename(defaultextension='.db',
              title = "save database structure in a text file",                          
              filetypes=[("default","*.sql"),("other","*.txt"),("all","*.*")])
       if filename == "": return
       with  io.open(filename,   'w', encoding='utf-8') as f:
           for line in self.conn.iterdump():
               f.write('%s\n' % line)
 
    def sav_script(self):
       """save a script in a file"""
       active_tab_id = self.n.notebook.select()
       if active_tab_id != '':
           #get current selection (or all)
           fw =self.n.fw_labels[active_tab_id]
           script = fw.get(1.0,END)[:-1]   
           filename = filedialog.asksaveasfilename(defaultextension='.db',
              title = "save script in a sql file",                          
              filetypes=[("default","*.sql"),("other","*.txt"),("all","*.*")])
       if filename == "": return
       with  io.open(filename,'w', encoding='utf-8') as f:
           f.write ("/*utf-8 bug safety : 你好 мир Artisou à croute blonde*/\n")
           f.write(script)        
 
    def attach_db(self):
       """attach an existing database"""
       filename = filedialog.askopenfilename(defaultextension='.db',
              title="Choose a database to attach ",    
              filetypes=[("default","*.db"),("other","*.db*"),("all","*.*")])
       attach = ((filename.replace("\\","/")).split("/")[-1]).split(".")[0]

       if filename != '':
           attach_order = "ATTACH DATABASE '%s' as '%s' "%(filename,attach);
           self.conn.execute(attach_order)
           self.actualize_db()


    def close_db(self):
       """close database"""
       try    : self.db_tree.delete("Database")
       except : pass
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
                self.add_thingsnew( id0, categ, att_db )


    def quit_db(self):
       """quit application button"""
       if messagebox.askyesno(message='Are you sure you want to quit ?',
	                      icon='question', title='Quiting'):
           self.tk_win.destroy()


    def run_tab(self):
       """clear previous results and run current script of a tab"""
       active_tab_id = self.n.notebook.select()
       if active_tab_id != '':
           #remove previous results
           self.n.remove_treeviews(active_tab_id)
           #get current selection (or all)
           fw =self.n.fw_labels[active_tab_id]
           try :
               script = (fw.get('sel.first', 'sel.last')) 
           except:
               script = fw.get(1.0,END)[:-1]   
           self.create_and_add_results(script, active_tab_id)
           fw.focus_set() #workaround of bug http://bugs.python.org/issue17511


    def chg_size(self  ):
        """change display size"""
        sizes=[10, 13, 14] 
        font_types =["TkDefaultFont","TkTextFont","TkFixedFont","TkMenuFont",
        "TkHeadingFont","TkCaptionFont","TkSmallCaptionFont","TkIconFont",
        "TkTooltipFont"]
        ww=['normal','bold']
        if self.font_size < max(sizes) :
            self.font_size=min([i for i in sizes  if i> self.font_size])
        else:
            self.font_size =sizes[0]; self.font_wheight  = 0
 
        ff='Helvetica' if self.font_size != min(sizes) else 'Courier';#'Times'
        self.font_wheight =  0 if  self.font_size == min(sizes) else 1
        for typ in font_types:
            default_font = font.nametofont(typ)
            default_font.configure(size=self.font_size,
                                   weight=ww[self.font_wheight], family=ff)

              
    def t_doubleClicked(self, event):
        "action on dbl_click on the Database structure" 
        #determine item to consider   
        selitem = self.db_tree.focus() #the item having the focus  
        seltag = self.db_tree.item(selitem,"tag")[0]  
        if seltag == "run_up" : # 'run-up' tag ==> dbl-click 1 level up 
            selitem =  self.db_tree.parent(selitem)
        #get final information : text, selection and action   
        definition , action = self.db_tree.item(selitem, "values")
        tab_text = self.db_tree.item(selitem, "text")
        script = action + " limit 999 " if action !="" else definition

        #create a new tab and run it if action suggest it
        new_tab_ref = self.n.new_query_tab(tab_text, script)
        if action != "" : self.run_tab() #run the new_tab created


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
R0lGODdhGAAYAKoAAP///56fnf9VAMzVzP9VMwAAAAAAAAAAACwAAAAAGAAYAAADZAi63P4wykmB
uO6KFnpX2raEnBeMGkgyZqsRoci2Znx9zKDjQGd7Dd2AFoiZgjuXEZhLomy9U3MojVk0PIUQt7re
kFSVTCxdbMsPLDgLYZ+JxDU8PuXN3c4JPqxHA84Ue2wPbAkAOw==
'''
        ,'deltabresult_img':'''\
R0lGODdhGAAYAJkAAP///56fnf8AAAAAACwAAAAAGAAYAAACXIyPBsu9CYObQDFbqcM16cZFondJ
z0ie33aA5nqGL4y4cCnf8cytdanr5HS/k0CAMhxzRyQu0Gw9m8gDtdhpNBdbIW/G7e5sDqprGBak
x0CAmXGVqsTlpciOOhYAADs=
'''
        ,'newtab_img':'''\
R0lGODdhGAAYAJkAAP///56fnQAAAAAAACwAAAAAGAAYAAACSoSPqcsm36KDsj1R1d00840E4ige
3xWSo9YppRGwGKPGCUrXtfQCut3ouYC5IHEhTCSHRt4x5fytIlKSs0l9HpZKLcy7BXOhRUYBADs=
'''
        ,'csvin_img':'''\
R0lGODdhGAAYAMwAAPj4+AAAADOqM2FkZtjY2r7Awujo6V9gYeDg4b/Cwzc3N0pKSl9fX5GRkVVV
VXl6fKSmpLCxsouNkFdXV97d4N7e4N7g4IyMjZyen6SopwAAAAAAAAAAAAAAAAAAAAAAACwAAAAA
GAAYAAAFlSAgjkBgmuUZlONKii4br/MLv/Gt47ia/rYcT2bb0VowVFFF8+2K0KjUJqhOo1XBlaQV
Zbdc7Rc8ylrJ5THaa5YqFozBgOFQAMznl6FhsO37UwMEBgiFFRYIhANXBxgJBQUJkpAZi1MEBxAR
kI8REAMUVxIEcgcDpqYEElcODwSvsK8PllMLAxeQkA0DDmhvEwwLdmAhADs=
'''
        ,'csvex_img':'''\
R0lGODdhGAAYAMwAAPj4+AAAADOqM2FkZtjY2r7AwuDg4b/Cw+jo6V9gYTc3N0pKSlVVVV9fX5GR
kaSmpLCxsnl6fIuNkN7g4N7d4KSop4yMjZyen1dXVwAAAAAAAAAAAAAAAAAAAAAAAAAAACwAAAAA
GAAYAAAFkiAgjkBgmuUZlONKii4br/MLv/Gt47ia/rYcT2bb0VowVFFF8+2K0Kh0JKhap1BrFZu9
cl9awZd03Y4BXvQ5DVUsGoNBg6FAm6MOhA3h4A4ICAaCBhOCCANYAxcHBQUHj44ViFMECQ8QjY0Q
DwMUWBIEcQkDo6MEElgMEQSsrawRk1MLAxaZBQ4DDGduGA0LdV8hADs=
'''
        ,'qryex_img':'''\
R0lGODdhGAAYAJkAAP///56fnQAAAP8AACwAAAAAGAAYAAACXIQPoporeR4yEtZ3J511e845zah1
oKV9WEQxqYOJX0rX9oDndp3jO6/7aXqDVOCIPB50Pk0yaQgCijSlITBt/p4B6ZbL3VkBYKxt7DTX
0BN2uowUw+NndVq+tk8KADs=
'''
        ,'sqlin_img':'''\
R0lGODdhGAAYALsAAP///46z2Xul02SJtp6fnenp6f8AAMLCwaHA4IODgoCo01RymIOPnmKGswAA
AAAAACwAAAAAGAAYAAAEkRDIOYm9N9G9SfngR2jclnhHqh7FWAKZF84uFxdr3pb3TPOWEy6n2tkG
jcZgyWw6OwOEdEqtIgYbRjTA7Xq/WIoW8S17wxOteR1AS9Ts8sI08Aru+Px9TknU9YB5fBN+AYGH
gxJ+dwoCjY+OCpKNiQAGBk6ZTgsGE5edLy+XlqOhop+gpiWoqqGoqa0Ur7CxABEAOw==
'''
        ,'sqlsav_img':'''\
R0lGODdhGAAYALsAAP///56fnZyen/8AAGSJtqHA4Hul0+jo6Y6z2cLCwaSmpIODgmKGs4yMjYOP
ngAAACwAAAAAGAAYAAAEgxDISacSOItVOxVHKB5C41mKsihH4r4kdyoEwxB4rhMnIDCFoHAY5J0E
BCFiyWQaPY6kYUqtGp6dxm6b60kG4LC3FwaPyeJzpzzwaDQTsbkTqNsx3zmgfapPAnt6Y3Z1Amlq
AoR3cF5+EoqFY4k9jpSAfQKSkJCDm4SZXpN9l5aUoB4RADs=
'''
        ,'dbdef_img':'''\
R0lGODdhGAAYAMwAAPj4+DOqM2SJtmFkZqHA4NjY2sLCwejo6b7Awpyen3ul046z2aSop+Dg4V9g
YZGRkaSmpLCxsouNkDc3N2dxekpKSlVVVYyMjWKGs4ODgnl6fJ+goYOPnl9fX0xMTAAAACwAAAAA
GAAYAAAFuCAgjuTIJGiaZGVLJkcsH9DjmgxzMYfh/4fVDcAQCDDGpNI4hGAI0KgUKhgmBNGFdrut
3jhYhXhMVnhdj6U6OWy7h4G4/O2Sx+n1OZ5kD5QmHgOCAx0TJXN3Iw8HLQc2InoAfiIUBQcNmJkN
BxSSiS0DCT8/CAYMA55DBQMQEQilCBGndBKrAw4Ot7kFEm+rG66vsRCob7WCube3vG8WGgXQ0dAa
nW8VAxfCCA8DFnsAExUWAxWGeCEAOw==
'''
       ,'chgsz_img':'''\
R0lGODdhGAAYAJkAAP///wAAADOqMwCqMywAAAAAGAAYAAACZISPGRvpb1iDRjy5KBBWYc0NXjQ9
A8cdDFkiZyiIwDpnCYqzCF2lr2rTHVKbDgsTJG52yE8R0nRSJA7qNOhpVbFPHhdhPF20w46S+f2h
xlzceksqu6ET7JwtLRrhwNt+1HdDUQAAOw==
'''
      }   
        #transform 'in place' base64 icons into tk_icons 
        for key, value in icons.items():
            icons[key] = PhotoImage(data = value)
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
                    ) #font = ( "tahoma", "13", "normal" ) )
            label.pack( ipadx = 1 )
        
        def close( event ):
            global tipwindow
            tw = tipwindow
            tipwindow = None
            if tw: tw.destroy()
            
        widget.bind( "<Enter>", enter )
        widget.bind( "<Leave>", close )


    def add_thingsnew(self, root_id , what , attached_db = ""): 
        "add a sub-tree to database tree pan"
        tables = get_things(self.conn,  what, attached_db) 
        #level 1 : create  the "what" node (as not empty)
        id = lambda t: ('"%s".'%t.replace('"', '""')) if t !="" else t 
        attached = id(attached_db) 
        if len(tables)>0:
            idt = self.db_tree.insert(root_id,"end","%s%s"%(attached, what)
                   , text="%s (%s)" % (what, len(tables)) , values=("","") )  
            #Level 2 : print object creation, and '(Definition)' if Table/View
            for tab in tables:
                definition = tab[2] ; sql3 = ""
                if tab[3] != '':
                    #it's a table : prepare a Query with names of each column
                    colnames = [col[1] for col in tab[3]]
                    columns = [col[0] for col in tab[3]]
                    sql3 = 'select "'+'" , "'.join(colnames)+'"  from ' + (
                            '%s"%s"'% (attached,tab[1])  )
                idc = self.db_tree.insert(idt,"end",  "%s%s" % (attached,tab[0]) 
                     ,text=tab[1],tags=('run',) , values=(definition,sql3))                    
                if sql3 != "":
                    self.db_tree.insert(idc,"end",("%s%s.%s"% (attached,tab[1], -1)),
                    text = ['(Definition)'],tags=('run',), values=(definition,""))
                    #level 3 : Insert a line per column of the Table/View
                    for c in range(len(columns)):
                        self.db_tree.insert(idc,"end",
                           ("%s%s.%s" % (attached, tab[1], c)),
                           text = columns[c], tags = ('run_up',), values = ('',''))
        return [i[1] for i in tables]


    def create_and_add_results(self, instructions, tab_tk_id):
        """execute instructions and add them to given tab results"""
        a_jouer = self.conn.get_sqlsplit(instructions, remove_comments = False) 
        #must read :https://www.youtube.com/watch?v=09tM18_st4I#t=1751
        #stackoverflow.com/questions/15856976/transactions-with-python-sqlite3
        isolation = self.conn.conn.isolation_level 
        if isolation == "" : #Python default, inconsistent with default dump.py
            self.conn.conn.isolation_level = None #right behavior 
        cu = self.conn.conn.cursor() ; sql_error = False
        for instruction in a_jouer:  
            instru = self.conn.get_sqlsplit(instruction, 
                                            remove_comments = True)[0]
            instru = instru.replace(";","").strip(' \t\n\r')
            first_line = (instru+"\n").splitlines()[0]   
            if instru[:5] == "pydef" :
                pydef = self.conn.createpydef(instru)
                titles = ("Creating embedded python function",)
                rows = self.conn.conn_def[pydef]['pydef'].splitlines()
                rows.append(self.conn.conn_def[pydef]['inst'])
                self.n.add_treeview(tab_tk_id, titles, rows, "Info", pydef)
            elif instruction != "":
                try :
                    cur = cu.execute(instruction)
                    rows = cur.fetchall()
                    #A query may have no result( like for an "update")
                    if cur.description != None :
                        titles = [row_info[0] for row_info in cur.description]
                        self.n.add_treeview(tab_tk_id, titles, rows,
                                        "Qry", first_line)
                except sqlite.Error as msg:#OperationalError
                    self.n.add_treeview(tab_tk_id, ('Error !',), [(msg,)],
                                        "Error !", first_line )
                    sql_error = True                    
                    break               

        try :
            if self.conn.conn.in_transaction : #python 3.2
                if not sql_error: cu.execute("COMMIT;")
                else : cu.execute("ROLLBACK;")
        except:
            if not sql_error:
                try :    cu.execute("COMMIT;")
                except : pass    
            else :
                try : cu.execute("ROLLBACK;")
                except : pass    
            
        self.conn.conn.isolation_level = isolation #restore standard

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
        fw_label = Text(f1 ,bd =1)
                
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
       if given_tk_id !='': self.notebook.forget(given_tk_id)


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

        #ttk.Style().configure('TLabelframe.label', font=("Arial", 14, "bold"))
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
    try:
        dlines = list(csv.reader(data_is.replace('\n\n','\n').splitlines()
            ,delimiter = separ, quotechar = quoter))
    except: #minimal hack for python2.7
        dlines = list(csv.reader(data_is.replace('\n\n','\n').splitlines()
            ,delimiter = str(separ), quotechar = str(quoter) ))
    r , typ = list(dlines[0]) , list(dlines[1]) 
    for i in range(len(r)):
        try:
            float (typ[i].replace(decim,'.'))
            typ[i] = 'REAL'
        except:
            typ[i] = 'TEXT'
    if header:
        head = ",\n".join([('"%s" %s'%(r[i],typ[i])) for i in range(len(r))])
        sql_crea = ('CREATE TABLE "%s" (%s);'  % (table_name, head))
    else:
        head = ",".join(["c_"+("000" +str(i))[-3:] for i in range(len(r))])
        sql_crea = ('CREATE TABLE "%s" (%s);'  % (table_name, head))
    return sql_crea, typ   , head                 

     
def import_csvtb(actions):
    """import csv dialog (with guessing of encoding and separator)"""
    csv_file = filedialog.askopenfilename(defaultextension='.db',
              title="Choose a csv fileto import ",
              filetypes=[("default","*.csv"),("other","*.txt"),("all","*.*")])
    #Guess encoding
    encodings = Guess_encoding(csv_file)
    #Guess Header and delimiter
    with io.open(csv_file, encoding = encodings[0]) as f:
        preview = f.read(9999)  
        has_header = True ; default_sep=","  ; default_quote='"'  
    try:
        dialect = csv.Sniffer().sniff(preview)
        has_header = csv.Sniffer().has_header(preview)
        default_sep = dialect.delimiter
        default_quote = Dialect.quotechar
    except:  pass #sniffer can fail
    default_decim = [".",","] if default_sep != ";" else [",","."]
        
    #Request form : List of Horizontal Frame names 'FramLabel' 
    #    or fields :  'Label', 'InitialValue',['r' or 'w', Width, Height]
    table_name = (csv_file.replace("\\","/")).split("/")[-1].split(".")[0]
    dlines = "\n\n".join(preview.splitlines()[:3])
    guess_sql = guess_sql_creation(table_name, default_sep, default_decim,
                                    has_header, dlines, default_quote)[2]
    fields_in = ['',[ 'csv Name', csv_file , 'r', 100],''
     ,['table Name', table_name]
     ,['column separator', default_sep, 'w', 20]
     ,['string delimiter', default_quote, 'w', 20]
     ,'',['Decimal separator', default_decim]
     ,['Encoding', encodings  ]
     ,'Fliflaps',['Header line', has_header]
     ,['Create table', True  ]
     ,['Replace existing data', True] ,''
     ,['first 3 lines' , dlines,'r', 100,10] ,''
     ,['use manual creation request', False],''
     ,['creation request', guess_sql,'w', 100,10]   ]
 
    create_dialog(("Importing %s" % csv_file ), fields_in  
                  , ("Import", import_csvtb_ok), actions )  


def Guess_encoding(csv_file):
    with io.open(csv_file, "rb") as f:
        data = f.read(5)
    if data.startswith(b"\xEF\xBB\xBF"): # UTF-8 with a "BOM"
        return ["utf-8-sig"]
    elif data.startswith(b"\xFF\xFE") or data.startswith(b"\xFE\xFF"): # UTF-16
        return ["utf-16"]
    else: #in Windows, guessing utf-8 doesn't work, so we have to try
        try:
            with io.open(csv_file, encoding = "utf-8") as f:
                preview = f.read(222222)  
                return ["utf-8"]
        except:
            return [locale.getdefaultlocale()[1], "utf-8"]


def export_csv_dialog(query = "select 42", text="undefined.csv", actions=[]):
    "export csv dialog"
    #Proposed encoding (we favorize utf-8 or utf-8-sig)
    encodings = ["utf-8",locale.getdefaultlocale()[1],"utf-16","utf-8-sig"]
    if os.name == 'nt': 
        encodings = ["utf-8-sig",locale.getdefaultlocale()[1],"utf-16","utf-8"]
    #Proposed csv separator
    default_sep=[",","|",";"]

    csv_file = filedialog.asksaveasfilename(defaultextension='.db',
              title = text,                          
              filetypes=[("default","*.csv"),("other","*.txt"),("all","*.*")])
    if csv_file != "":
        #Request form (http://www.python-course.eu/tkinter_entry_widgets.php)
        fields = ['',['csv Name', csv_file,'r',100 ],''
           ,['column separator',default_sep]
           ,['Header line',True]
           ,['Encoding',encodings], ''
           ,["Data to export (MUST be 1 Request)" ,(query), 'w', 100,10] ] 
 
        create_dialog(("Export to %s" % csv_file), fields ,
                  ("Export",  export_csv_ok) , actions)


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
                fw_label = Text(d_frame, bd=1, width=width, height=height)
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
            else : #Text or Combo
                namelbl = ttk.Label(packing_frame,   text=field[0] )
                namelbl.grid(column=0, row=0, sticky='nsw', pady=5, padx=5)
                name_var = StringVar()
                if not isinstance(field[1], (list, tuple)) :
                    name = ttk.Entry(packing_frame, textvariable = name_var,
                                 width=width, state = status)
                    name_var.set(field[1])
                else:
                    name = ttk.Combobox(packing_frame, textvariable=name_var, 
                                state = status)
                    name['values'] = list(field[1])
                    name.current(0)
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


def import_csvtb_ok(thetop, entries, actions):
    "read input values from tk formular"
    conn  , actualize_db = actions
    #build dico of result
    d={f[0]:f[1]()  for f in entries if type(f)!= type('e')}
    #affect to variables
    csv_file = d['csv Name'].strip()
    table_name = d['table Name'].strip()
    separ = d['column separator'] ; decim = d['Decimal separator'] 
    quotechar = d['string delimiter']
    #Action
    if   csv_file != "(none)" and len(csv_file)*len(table_name)*len(separ)>1:
        thetop.destroy()
        curs = conn.conn.cursor()
        #Do initialization job
        sql, typ, head = guess_sql_creation(table_name, separ, decim,
                              d['Header line'], d["first 3 lines"], quotechar)
        if d['Create table']:
            curs.execute('drop TABLE if exists "%s";' % table_name)
            if d['use manual creation request']:
                sql = ('CREATE TABLE "%s" (%s);'  % 
                       (table_name, d["creation request"]))
            curs.execute(sql )
        if d['Replace existing data'] :
            curs.execute('delete from "%s";' % table_name)
        sql='INSERT INTO "%s"  VALUES(%s);' % (
               table_name,  ", ".join(["?"]*len(typ)))

        try:
            reader = csv.reader(open(csv_file, 'r', encoding = d['Encoding']),
                           delimiter = separ, quotechar = quotechar)
        except: #minimal hack for 2.7
            reader = csv.reader(open(csv_file, 'r' ),
                           delimiter = str(separ), quotechar=str(quotechar) )
        #read first_line if needed to skip headers 
        if d['Header line']:
            row = next(reader)
        if decim != "." : # one by one needed
            for row in reader:
               if type(row) !=type ("e"):
                   for i in range(len(row)): 
                       row[i] = row[i].replace( decim,  ".") 
               curs.execute(sql, row)
        else :
            curs.executemany(sql, reader)
        conn.conn.commit()
        actualize_db()


def export_csv_ok(thetop, entries, actions):
    "export a csv table (action)"
    conn = actions[0]
    import csv
    #build dico of result
    d={f[0]:f[1]()  for f in entries if type(f)!= type('e')}

    csv_file=d['csv Name'].strip() 
    cursor = conn.conn.cursor()
    cursor.execute(d["Data to export (MUST be 1 Request)"])
    thetop.destroy()
    if sys.version_info[0] !=2: #python3
        fout = io.open(csv_file, 'w', newline = '', encoding= d['Encoding'])
        writer = csv.writer(fout, delimiter = d['column separator'],
                            quotechar='"', quoting=csv.QUOTE_MINIMAL)
    else: #python2.7 (minimal)   
        fout = io.open(csv_file, 'wb')
        writer = csv.writer(fout, delimiter = str(d['column separator']),
                        quotechar=str('"'), quoting=csv.QUOTE_MINIMAL)
    if d['Header line']:
            writer.writerow([i[0] for i in cursor.description]) # heading row
    writer.writerows(cursor.fetchall())
    fout.close
    

def export_csvtb( actions):
    "get selected table definition and launch cvs export dialog"
    #determine selected table   
    db_tree = actions[1]
    selitem = db_tree.focus() #get tree item having the focus  
    if selitem !='':
        seltag = db_tree.item(selitem,"tag")[0] 
        if seltag == "run_up" : # if 'run-up', do as if dbl-click 1 level up 
            selitem =  db_tree.parent(selitem)
        #get final information 
        definition , query = db_tree.item(selitem, "values")
        if query != "": #run the export_csv dialog
            title = ('Export Table "%s" to ?' %db_tree.item(selitem, "text"))
            export_csv_dialog(query, title, actions )   

              
def export_csvqr( actions):
    "get tab selected definition and launch cvs export dialog"
    n = actions[1]
    active_tab_id = n.notebook.select()
    if active_tab_id !='': #get current selection (or all)
        fw =n.fw_labels[active_tab_id]
        try : query = fw.get('sel.first', 'sel.last')
        except: query = fw.get(1.0,END)[:-1]   
        if query != "":  export_csv_dialog(query , "Export Query", actions)   

    
def get_things( conn,   what , attached_db = "", tbl =""):
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
    id = lambda t: ('"%s".'%t.replace('"', '""')) if t !="" else t 
    attached = id(attached_db) 
    order = dico[what] if type(dico[what]) != type('e') else dico[dico[what]] 
    Tables = []
    if what == "pydef": #pydef request is not sql
        resu = [[k , v['pydef']] for k, v in conn.conn_def.items()]

    else:
        #others are sql request
        resu = conn.execute(order[0].format(attached,what,tbl)).fetchall()
        #result must be transformed in a list, and attached db 'main' removed
        resu = list(resu) if what != 'attached_databases' else list(resu)[1:]
    #generate tree list for this 'what' category level :
    #     [objectCode, objectName, Definition, [Level below] or '']
    for rec in resu:
        result = [order[i].format(*rec) for i in range(1,5)]
        if result[3] != '':
            resu2 = get_things(conn,    result[3] ,
                               attached_db , result[1])
            result[3] = resu2
        Tables.append(result)
    return Tables    


class baresql():
    "a tiny sql wrapper"
    def __init__(self, connection="", keep_log = False, cte_inline = True):
        self.dbname = connection.replace(":///","://").replace("sqlite://","")
        self.conn = sqlite.connect(self.dbname,
                   detect_types = sqlite.PARSE_DECLTYPES)
        #pydef and logging infrastructure
        self.conn_def = {}
        self.do_log = keep_log
        self.log = []
        
    def close(self):
        self.conn.close
        self.conn_def = {}
            
    def iterdump(self):
        "slightly improved database dump over default sqlite3 module dump"
        #Force detection of utf-8
        yield("/*utf-8 bug safety : 你好 мир Artisou à croute blonde*/\n")
        #Add the Python functions pydef 
        for k in self.conn_def.values():   
            yield(k['pydef'] + ";\n" ) 
        #Disable Foreign Constraints at Load 
        yield("PRAGMA foreign_keys = OFF; /*if SQlite */;")        
        yield("\n/* SET foreign_key_checks = 0;/*if Mysql*/;")
        #How-to parametrize Mysql to SQL92 standard 
        yield("/* SET sql_mode = 'PIPES_AS_CONCAT';/*if Mysql*/;")
        yield("/* SET SQL_MODE = ANSI_QUOTES; /*if Mysql*/;\n")
        #Now the standard dump (notice it uses BEGIN TRANSACTION) 
        for line in self.conn.iterdump():
               yield( line)
        #Re-instantiate Foreign_keys = True
        for row in self.conn.execute("PRAGMA foreign_keys"):
            flag = 'ON' if row[0] == 1 else 'OFF'
            yield("PRAGMA foreign_keys = %s;/*if SQlite*/;"%flag)        
            yield("PRAGMA foreign_keys = %s;/*if SQlite, twice*/;"%flag)        
            yield("\n/*SET foreign_key_checks = %s;/*if Mysql*/;\n"%row[0])
        
    def execute(self, sql , env = None):
        "execute sql but intercept log"
        if self.do_log: self.log.append(sql)
        return self.conn.execute(sql )        

    def createpydef(self, sql):
        "generates and registr a pydef instruction"
        instruction = sql.strip('; \t\n\r')
        #create Python function in Python
        exec(instruction[2:]  , globals() , locals())        
        #add Python function in SQLite
        firstline=(instruction[5:].splitlines()[0]).lstrip()
        firstline = firstline.replace(" ","") + "(" 
        instr_name=firstline.split("(",1)[0].strip()
        instr_parms=firstline.count(',')+1
        instr_add = "self.conn.create_function('%s', %s, %s)" %(
           instr_name,instr_parms, instr_name)
        exec(instr_add , globals() , locals())
        #housekeeping definition of pydef in a dictionnary 
        the_help= dict(globals(),**locals())[instr_name].__doc__
        self.conn_def[instr_name]={'parameters':instr_parms, 'inst':instr_add,
                                  'help':the_help, 'pydef':instruction}
        return instr_name

                
    def get_token(self, sql, start = 0):
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


    def get_sqlsplit(self, sql, remove_comments=False):
        """split an sql file in list of separated sql orders"""
        beg = end = 0; length = len(sql) ; trigger_mode = False
        sqls = []
        while end < length-1:
            #Special case for Trigger : semicolumn don't count
            tk_end , token = self.get_token(sql,end)
            if token == 'TK_OTHER':
                tok = sql[end:tk_end].upper();
                if tok == "TRIGGER": 
                    trigger_mode = True; translvl = 0
                elif trigger_mode and tok in('BEGIN','CASE'): translvl += 1
                elif trigger_mode and tok == 'END' :  
                    translvl -= 1
                    if translvl <=0 : trigger_mode = False
            elif (token == 'TK_SEMI' and not trigger_mode) or tk_end == length: 
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
INSERT INTO item values("T","Ford",1000);
INSERT INTO item select "A","Merced",1250 union all select "W","Wheel",9 ;
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

