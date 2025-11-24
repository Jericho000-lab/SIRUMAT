import gspread
import os

print("Initializing Inventaris_Barang Worksheet...")

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
    
    worksheet_name = "Inventaris_Barang"
    try:
        ws = sh.worksheet(worksheet_name)
        print(f"Worksheet '{worksheet_name}' already exists.")
    except gspread.WorksheetNotFound:
        print(f"Worksheet '{worksheet_name}' not found. Creating...")
        ws = sh.add_worksheet(title=worksheet_name, rows=1000, cols=10)
        # Add headers
        headers = ["Nama Barang", "Kategori", "Stok", "Satuan", "Min Stok", "Terakhir Update"]
        ws.append_row(headers)
        print(f"Created '{worksheet_name}' with headers: {headers}")
        
        # Add some dummy data for testing
        dummy_data = [
            ["Sabun Cuci Tangan", "Kebersihan", "10", "Botol", "5", "-"],
            ["Tisu Toilet", "Kebersihan", "50", "Roll", "20", "-"],
            ["Kertas A4", "ATK", "5", "Rim", "2", "-"]
        ]
        for row in dummy_data:
            ws.append_row(row)
        print("Added dummy data.")

except Exception as e:
    print(f"CRITICAL ERROR: {e}")
