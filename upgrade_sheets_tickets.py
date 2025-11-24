import gspread
import os

print("Upgrading Sheets for Ticketing System...")

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
    
    # 1. Upgrade Laporan_Kerusakan
    try:
        ws_laporan = sh.worksheet("Laporan_Kerusakan")
        headers = ws_laporan.row_values(1)
        
        if "Tiket ID" not in headers:
            print("Adding 'Tiket ID' and 'Status' to Laporan_Kerusakan...")
            # Append columns to header
            ws_laporan.update_cell(1, len(headers) + 1, "Tiket ID")
            ws_laporan.update_cell(1, len(headers) + 2, "Status")
            
            # Update existing rows with default values
            all_values = ws_laporan.get_all_values()
            if len(all_values) > 1:
                # Generate dummy IDs for existing rows to avoid breaking
                updates = []
                for i in range(2, len(all_values) + 2):
                    # Ticket ID: TKT-OLD-{i}
                    # Status: Selesai (Assume old ones are done or let user decide, setting Selesai for safety)
                    ws_laporan.update_cell(i, len(headers) + 1, f"TKT-OLD-{i}")
                    ws_laporan.update_cell(i, len(headers) + 2, "Selesai")
                    print(f"Updated row {i}")
        else:
            print("Laporan_Kerusakan already has Ticket columns.")
            
    except Exception as e:
        print(f"Error updating Laporan_Kerusakan: {e}")

    # 2. Upgrade Laporan_Perbaikan
    try:
        ws_perbaikan = sh.worksheet("Laporan_Perbaikan")
        headers = ws_perbaikan.row_values(1)
        
        if "Tiket ID" not in headers:
            print("Adding 'Tiket ID' to Laporan_Perbaikan...")
            ws_perbaikan.update_cell(1, len(headers) + 1, "Tiket ID")
        else:
            print("Laporan_Perbaikan already has Ticket columns.")
            
    except Exception as e:
        print(f"Error updating Laporan_Perbaikan: {e}")

    print("Upgrade Complete!")

except Exception as e:
    print(f"CRITICAL ERROR: {e}")
