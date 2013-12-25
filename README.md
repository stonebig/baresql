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

 * extending python sql motor with a basic CTE (Common Table Expression),
 * Travis-CI infrastructure
 * allowing other databases (via pyqt ?).

Help is welcome.


Inspiration :
-------------
 * pypi.python.org/pypi/pandasql‎: bringing sql over python objects via pandas trick,
 * pypi.python.org/pypi/ipython-sql/ipython-sql :  sql magic

Version : 
---------
 * 0.1 : initial version
 * 0.2 : add "range(10)" iterable object support 
 * 0.3 (dev) : will include a basic CTE
