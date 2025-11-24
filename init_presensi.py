import gspread
import os

print("Initializing Presensi_PPNPN Worksheet...")

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
    
    worksheet_name = "Presensi_PPNPN"
    try:
        ws = sh.worksheet(worksheet_name)
        print(f"Worksheet '{worksheet_name}' already exists.")
    except gspread.WorksheetNotFound:
        print(f"Worksheet '{worksheet_name}' not found. Creating...")
        ws = sh.add_worksheet(title=worksheet_name, rows=1000, cols=10)
        # Add headers
        headers = ["Waktu", "Nama Pegawai", "Status", "Keterangan", "Bukti Foto"]
        ws.append_row(headers)
        print(f"Created '{worksheet_name}' with headers: {headers}")

except Exception as e:
    print(f"CRITICAL ERROR: {e}")
