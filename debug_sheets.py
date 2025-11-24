import gspread
import os

print("Starting Worksheet Debugger...")

if not os.path.exists('service_account.json'):
    print("ERROR: service_account.json not found!")
    exit()

try:
    gc = gspread.service_account(filename='service_account.json')
    
    # Open the spreadsheet found in the previous step
    sh = gc.open("database_sirumat")
    print(f"Connected to spreadsheet: {sh.title}")
    
    print("Listing worksheets:")
    ws_list = sh.worksheets()
    existing_sheets = [ws.title for ws in ws_list]
    for ws in ws_list:
        print(f"- {ws.title}")
        
    required_sheets = ["Laporan_Kerusakan", "Checklist_Kebersihan", "Rencana_Konten"]
    missing_sheets = [s for s in required_sheets if s not in existing_sheets]
    
    if missing_sheets:
        print(f"WARNING: The following required worksheets are MISSING: {missing_sheets}")
        print("Attempting to create them...")
        for s in missing_sheets:
            try:
                sh.add_worksheet(title=s, rows=100, cols=10)
                print(f"Created worksheet: {s}")
                # Add headers
                ws = sh.worksheet(s)
                if s == "Laporan_Kerusakan":
                    ws.append_row(["Tanggal", "Nama Pelapor", "Lokasi", "Kendala", "Bukti Foto"])
                elif s == "Checklist_Kebersihan":
                    ws.append_row(["Tanggal", "Nama Petugas", "Area", "Kondisi", "Bukti Foto"])
                elif s == "Rencana_Konten":
                    ws.append_row(["Tanggal", "Caption", "Platform", "Status"])
                print(f"Added headers to {s}")
            except Exception as e:
                print(f"ERROR creating worksheet {s}: {e}")
    else:
        print("All required worksheets exist.")
        
    # Test writing to Laporan_Kerusakan again
    print("Attempting to write test row to Laporan_Kerusakan...")
    ws = sh.worksheet("Laporan_Kerusakan")
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ws.append_row([f"TEST_WRITE_2_{timestamp}", "System", "Debug", "Second Connection Test", "-"])
    print("Write successful. Please check the spreadsheet.")

except Exception as e:
    print(f"CRITICAL ERROR: {e}")
