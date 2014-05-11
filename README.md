baresql
=======

making sql simpler for bare python users.

 * Author : github.com/stonebig
 * Licence : MIT (should it be BSD 3-clause ? not an expert)


Goals
------
baresql improves sql agility of python data science beginners by :
 * allowing sql over python objects (list, ranges, ...) and SQL Tables,
 * requiring no special module except : pandas. 

By default baresql is tested on windows/python3.3 (winpython3.3)

Examples
--------
http://nbviewer.ipython.org/github/stonebig/baresql/blob/master/examples/baresql_with_cte.ipynb

http://nbviewer.ipython.org/github/stonebig/baresql/blob/master/examples/baresql_with_cte_code_included.ipynb

To Do :
-------

 * ~~extending python sql motor with a basic CTE (Common Table Expression),~~
 * ~~allowing mysql database (via pandas 0.11+)~~
 * allowing other databases (via pandas 0.14+ and sqlalchemy)
 * Travis-CI infrastructure

Help is welcome.


Inspiration :
-------------
 * pypi.python.org/pypi/pandasql‎: bringing sql over python objects via pandas trick,
 * pypi.python.org/pypi/ipython-sql/ipython-sql :  sql magic

Version : 
---------
 * 0.1 : initial version
 * 0.2 : add "range(10)" iterable object support 
 * 0.3 : includes a basic CTE
 * 0.3.2 : support comments in the SQL
 * 0.4 : rewrite with token
 * 0.4.1 : inline CTE when syntax is "with x as (y)"
 * 0.5 : use SQLite true CTE if SQLite >= 3.8.3
 * 0.5.1 : bug correction + SQLite3.8.3 beta from 2013-01-22
 * 0.6 : first version with correct mysql support
 * 0.6.1 : a pure standard-installation Python SQLite browser in examples\sqlite_py_manager.py 
        https://github.com/stonebig/baresql/blob/master/examples/sqlite_py_manager.GIF
 * 0.7dev : support of pandas 0.14 sqlalchemy
 
