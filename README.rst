baresql : playing SQL directly on Python datas
==============================================

baresql improves sql agility of python data science beginners by :
 * allowing sql over python objects (list, ranges, ...) and SQL Tables,
 * requiring no special module except : pandas. 

Inspiration :
-------------

* pypi.python.org/pypi/pandasql : sqldf for pandas
 
* pypi.python.org/pypi/ipython-sql :  sql magic in Ipython


Features
--------

* query lists , tuple, dictionnaries, dataframes 

* result as a dataframe, list of records, or list

* basic Common Table Expression support on old python3.3- versions


Installation
------------

You can install, upgrade, uninstall sqlite_bro.py with these commands::

  $ pip install baresql
  $ pip install --upgrade baresql
  $ pip uninstall baresql

or just launch it from IPython with %load https://raw.githubusercontent.com/stonebig/baresql/master/baresql/baresql.py

or just copy the file 'sqlite_bro.py' to any pc (with python installed)

Basic Example 
-------------

::

  from __future__ import print_function, unicode_literals, division  # if Python2.7
  from baresql import baresql
  bsqldf = lambda q: bsql.df(q, dict(globals(),**locals()))
  
  users = ['Alexander', 'Bernard', 'Charly', 'Danielle', 'Esmeralda', 'Franz']
  #  We use the python 'users' list like a SQL table
  sql = "select 'Welcome ! ' , * from users$$"
  bsqldf(sql)
 

Examples
--------
http://nbviewer.ipython.org/github/stonebig/baresql/blob/master/examples/baresql_with_cte.ipynb

Links
-----

* `Fork me on GitHub <http://github.com/stonebig/baresql>`_