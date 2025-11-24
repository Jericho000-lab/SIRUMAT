import gspread
import pandas as pd
import os

print("Starting Data Verification...")

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
    
    ws = sh.worksheet("Laporan_Kerusakan")
    print(f"Worksheet: {ws.title}")
    
    # Get all values
    all_values = ws.get_all_values()
    total_rows = len(all_values)
    print(f"Total rows found: {total_rows}")
    
    print("\n--- Last 5 Rows ---")
    for i, row in enumerate(all_values[-5:]):
        print(f"Row {total_rows - 4 + i}: {row}")
        
    print("\n-------------------")
    
    # Check if the specific data from the screenshot is there
    # Data: 'joko widodo', 'solo'
    found = False
    for i, row in enumerate(all_values):
        if "joko widodo" in str(row):
            print(f"\nSUCCESS! Found 'joko widodo' at Row {i+1}")
            print(f"Content: {row}")
            found = True
            
    if not found:
        print("\nWARNING: 'joko widodo' NOT found in the sheet.")

except Exception as e:
    print(f"CRITICAL ERROR: {e}")
