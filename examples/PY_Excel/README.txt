Put for_PY_Excel_baresql_Part1.txt in a first =PY() cell , for example A1
Put for_PY_Excel_baresql_Part2.txt in a second =PY() cell , for example A2

you can now play the for_PY_Excel_example1.txt in a third =PY() cell , for example A4


remark, when reading tables from excel, read from a table "my_data" and specify you have header:
data = xl(my_data[#Tout], Header=True) # in french #Tout = #All .... hope it's international

