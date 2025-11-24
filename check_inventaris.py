import gspread
import os

print("Checking Inventaris_Barang Worksheet...")

if not os.path.exists('service_account.json'):
    print("ERROR: service_account.json not found!")
    exit()

try:
    gc = gspread.service_account(filename='service_account.json')
    try:
        sh = gc.open("database_sirumat")
    except gspread.SpreadsheetNotFound:
        sh = gc.open("Database_SiRumat")
    
    print(f"Connected to: {sh.title}")
    
    try:
        ws = sh.worksheet("Inventaris_Barang")
        print("SUCCESS: Worksheet 'Inventaris_Barang' exists.")
        print(f"Headers: {ws.row_values(1)}")
    except gspread.WorksheetNotFound:
        print("FAILURE: Worksheet 'Inventaris_Barang' does NOT exist.")

except Exception as e:
    print(f"ERROR: {e}")
