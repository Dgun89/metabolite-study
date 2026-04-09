import openpyxl

wb = openpyxl.load_workbook("metabolites_completed.xlsx")
ws = wb.active

#print(ws.title)
#print(ws.max_row)
#print(ws.max_column)

for row in ws.iter_rows(min_row=2, max_row=5, values_only=True):
    print(row[1])