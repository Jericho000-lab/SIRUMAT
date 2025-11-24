import streamlit as st
import pandas as pd
import os
import io
import gspread
import base64
from datetime import datetime

# Set page configuration
st.set_page_config(page_title="Si-Rumat", layout="wide")

# Constants
UPLOAD_DIR = "galeri_bukti"

# Helper functions
def ensure_upload_dir():
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)

def save_uploaded_file(uploaded_file):
    if uploaded_file is None:
        return None
    
    ensure_upload_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Sanitize filename just in case
    safe_filename = "".join(c for c in uploaded_file.name if c.isalnum() or c in "._- ")
    filename = f"{timestamp}_{safe_filename}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    with open(filepath, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return filepath

def get_image_data_url(file_path):
    """Reads a local image file and returns a Base64 Data URI."""
    if not file_path or file_path == "-" or not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        encoded = base64.b64encode(data).decode()
        # Determine mime type based on extension
        ext = os.path.splitext(file_path)[1].lower()
        mime = "image/png" if ext == ".png" else "image/jpeg"
        return f"data:{mime};base64,{encoded}"
    except Exception:
        return None

def generate_ticket_id():
    """Generates a unique ticket ID based on timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"TKT-{timestamp}"

def update_ticket_status(ticket_id, new_status):
    """Updates the status of a specific ticket in Laporan_Kerusakan."""
    conn = get_connection()
    if conn:
        try:
            ws = conn.worksheet("Laporan_Kerusakan")
            # Find the cell with the ticket ID
            cell = ws.find(ticket_id)
            if cell:
                # Status is in the column after Ticket ID (based on our upgrade script)
                # But safer to find header index. For now, assuming it's the last column or we search for it.
                # Let's find 'Status' column index
                headers = ws.row_values(1)
                if "Status" in headers:
                    status_col = headers.index("Status") + 1
                    ws.update_cell(cell.row, status_col, new_status)
                    return True
        except Exception as e:
            st.error(f"Failed to update ticket status: {e}")
    return False

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# Sidebar
with st.sidebar:
    st.title("Menu")
    menu = st.radio("Pilih Menu", ["Beranda", "Kerumahtanggaan", "Manajemen Inventaris", "Absensi PPNPN"])
    st.divider()
    debug_mode = st.checkbox("Debug Mode")

# Google Sheets Connection Helper
def get_connection():
    try:
        # Try loading from Streamlit secrets first (for Cloud)
        if "gcp_service_account" in st.secrets:
            service_account_info = st.secrets["gcp_service_account"]
            gc = gspread.service_account_from_dict(service_account_info)
        # Fallback to local file (for local development)
        elif os.path.exists('service_account.json'):
            gc = gspread.service_account(filename='service_account.json')
        else:
            st.error("Missing Google Sheets credentials. Please configure secrets or add service_account.json.")
            return None

        try:
            sh = gc.open("database_sirumat")
        except gspread.SpreadsheetNotFound:
            sh = gc.open("Database_SiRumat")
        return sh
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return None

def load_data(sheet_name):
    sh = get_connection()
    if sh is None:
        return pd.DataFrame()
        
    try:
        worksheet = sh.worksheet(sheet_name)
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except gspread.WorksheetNotFound:
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading data from {sheet_name}: {e}")
        return pd.DataFrame()

import time

def save_data(sheet_name, new_data):
    if debug_mode:
        st.write(f"DEBUG: Starting save to {sheet_name}...")
        st.write(f"DEBUG: Data: {new_data.values.tolist()}")

    sh = get_connection()
    if sh is None:
        if debug_mode: st.error("DEBUG: Connection failed (sh is None)")
        return False

    try:
        worksheet = sh.worksheet(sheet_name)
        if debug_mode: st.write(f"DEBUG: Worksheet '{sheet_name}' found. Appending row...")
        
        # Use append_row for single row insertion (safer/simpler)
        worksheet.append_row(new_data.values.tolist()[0])
        
        if debug_mode: st.success("DEBUG: append_row completed successfully!")
        return True
    except Exception as e:
        st.error(f"Error saving data to {sheet_name}: {e}")
        if debug_mode: st.error(f"DEBUG: Exception details: {e}")
        return False

# Main content
st.title("Si-Rumat")

if menu == "Beranda":
    st.header("Dashboard Statistik")
    
    # Load data for metrics
    df_kerusakan = load_data("Laporan_Kerusakan")
    df_perbaikan = load_data("Laporan_Perbaikan")

    # Calculate metrics
    total_kerusakan = len(df_kerusakan) if not df_kerusakan.empty else 0
    total_perbaikan = len(df_perbaikan) if not df_perbaikan.empty else 0

    # Display metrics
    col1, col2 = st.columns(2)
    col1.metric("Total Laporan Kerusakan", total_kerusakan)
    col2.metric("Total Perbaikan Selesai", total_perbaikan)

    st.divider()

    # Visualization
    st.subheader("Statistik Kerusakan per Lokasi")
    if not df_kerusakan.empty and "Lokasi" in df_kerusakan.columns:
        lokasi_counts = df_kerusakan["Lokasi"].value_counts()
        st.bar_chart(lokasi_counts)
    else:
        st.info("Belum ada data kerusakan untuk ditampilkan.")

elif menu == "Kerumahtanggaan":
    st.header("Kerumahtanggaan")
    tab1, tab2 = st.tabs(["Laporan Kerusakan", "Laporan Perbaikan"])

    with tab1:
        st.subheader("Laporan Kerusakan")
        with st.form("form_kerusakan"):
            c1, c2 = st.columns(2)
            nama_pelapor = c1.text_input("Nama Pelapor")
            lokasi = c2.text_input("Lokasi")
            kendala = st.text_area("Kendala/Kerusakan")
            uploaded_foto = st.file_uploader("Upload Bukti Foto", type=['png', 'jpg', 'jpeg'])
            submitted_kerusakan = st.form_submit_button("Kirim Laporan")

            if submitted_kerusakan:
                if nama_pelapor and lokasi and kendala:
                    foto_path = "-"
                    if uploaded_foto:
                        foto_path = save_uploaded_file(uploaded_foto)
                    
                    waktu_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    tiket_id = generate_ticket_id()
                    
                    data = pd.DataFrame({
                        "Tanggal": [waktu_sekarang],
                        "Nama Pelapor": [nama_pelapor],
                        "Lokasi": [lokasi],
                        "Kendala": [kendala],
                        "Bukti Foto": [foto_path],
                        "Tiket ID": [tiket_id],
                        "Status": ["Pending"]
                    })
                    
                    if save_data("Laporan_Kerusakan", data):
                        st.success(f"Laporan berhasil dikirim! Tiket ID: {tiket_id}")
                        if not debug_mode:
                            time.sleep(1)
                            st.rerun()
                else:
                    st.error("Mohon lengkapi semua field.")
        
        st.divider()
        st.subheader("Riwayat Laporan")
        df_kerusakan = load_data("Laporan_Kerusakan")
        if not df_kerusakan.empty:
            # Prepare display dataframe with images
            df_display = df_kerusakan.copy()
            if "Bukti Foto" in df_display.columns:
                df_display["Bukti Foto"] = df_display["Bukti Foto"].apply(get_image_data_url)

            st.dataframe(
                df_display, 
                use_container_width=True,
                column_config={
                    "Bukti Foto": st.column_config.ImageColumn("Bukti Foto", help="Bukti Foto Laporan"),
                    "Status": st.column_config.SelectboxColumn(
                        "Status",
                        options=["Pending", "Selesai"],
                        help="Status Pengerjaan",
                        disabled=True # Read-only in this view
                    )
                }
            )
            
            st.download_button(
                label="Download Excel",
                data=to_excel(df_kerusakan),
                file_name=f"Laporan_Kerusakan_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("Belum ada data laporan.")

    with tab2:
        st.subheader("Laporan Perbaikan")
        
        # Load Pending Tickets
        df_kerusakan = load_data("Laporan_Kerusakan")
        pending_tickets = []
        if not df_kerusakan.empty and "Status" in df_kerusakan.columns:
            pending_tickets = df_kerusakan[df_kerusakan["Status"] == "Pending"]["Tiket ID"].tolist()
        
        selected_ticket = st.selectbox("Pilih Tiket Kerusakan (Pending)", ["Non-Tiket (Manual)"] + pending_tickets)
        
        with st.form("form_perbaikan"):
            c1, c2 = st.columns(2)
            nama_teknisi = c1.text_input("Nama Teknisi")
            
            # Auto-fill location if ticket selected
            default_lokasi = ""
            if selected_ticket != "Non-Tiket (Manual)" and not df_kerusakan.empty:
                ticket_row = df_kerusakan[df_kerusakan["Tiket ID"] == selected_ticket]
                if not ticket_row.empty:
                    default_lokasi = ticket_row.iloc[0]["Lokasi"]
            
            lokasi_perbaikan = c2.text_input("Lokasi Perbaikan", value=default_lokasi)
            tindakan = st.text_area("Tindakan Perbaikan")
            bukti_foto_perbaikan = st.file_uploader("Upload Foto Perbaikan", type=["png", "jpg", "jpeg"])
            
            submitted_perbaikan = st.form_submit_button("Simpan & Selesaikan Tiket")
            
            if submitted_perbaikan:
                if nama_teknisi and lokasi_perbaikan and tindakan:
                    foto_path = "-"
                    if bukti_foto_perbaikan:
                        foto_path = save_uploaded_file(bukti_foto_perbaikan)
                    
                    waktu_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    data = pd.DataFrame({
                        "Tanggal": [waktu_sekarang],
                        "Nama Teknisi": [nama_teknisi],
                        "Lokasi": [lokasi_perbaikan],
                        "Tindakan Perbaikan": [tindakan],
                        "Bukti Foto": [foto_path],
                        "Tiket ID": [selected_ticket if selected_ticket != "Non-Tiket (Manual)" else "-"]
                    })
                    
                    if save_data("Laporan_Perbaikan", data):
                        # Update status if it's a ticket
                        if selected_ticket != "Non-Tiket (Manual)":
                            update_ticket_status(selected_ticket, "Selesai")
                            st.success(f"Laporan perbaikan disimpan dan Tiket {selected_ticket} ditandai Selesai!")
                        else:
                            st.success("Laporan perbaikan berhasil disimpan!")
                            
                        if not debug_mode:
                            time.sleep(1)
                            st.rerun()
                else:
                    st.error("Mohon lengkapi semua field.")
        
        st.divider()
        st.subheader("Riwayat Perbaikan")
        df_perbaikan = load_data("Laporan_Perbaikan")
        if not df_perbaikan.empty:
            # Prepare display dataframe with images
            df_display = df_perbaikan.copy()
            if "Bukti Foto" in df_display.columns:
                df_display["Bukti Foto"] = df_display["Bukti Foto"].apply(get_image_data_url)

            st.dataframe(
                df_display, 
                use_container_width=True,
                column_config={
                    "Bukti Foto": st.column_config.ImageColumn("Bukti Foto", help="Bukti Foto Perbaikan")
                }
            )
            
            st.download_button(
                label="Download Excel",
                data=to_excel(df_perbaikan),
                file_name=f"Laporan_Perbaikan_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("Belum ada data perbaikan.")




elif menu == "Manajemen Inventaris":
    st.header("Manajemen Inventaris (OfficeOps)")
    
    tab1, tab2 = st.tabs(["Stok Barang", "Update Stok"])
    
    with tab1:
        st.subheader("Daftar Stok Barang")
        df_inventaris = load_data("Inventaris_Barang")
        
        if not df_inventaris.empty:
            # Convert numeric columns
            if "Stok" in df_inventaris.columns:
                df_inventaris["Stok"] = pd.to_numeric(df_inventaris["Stok"], errors='coerce').fillna(0)
            if "Min Stok" in df_inventaris.columns:
                df_inventaris["Min Stok"] = pd.to_numeric(df_inventaris["Min Stok"], errors='coerce').fillna(0)
            
            # Styling function
            def highlight_stock(row):
                try:
                    stok = float(row["Stok"])
                    min_stok = float(row["Min Stok"])
                    if stok == 0:
                        return ['background-color: #ffcccc'] * len(row) # Red
                    elif stok <= min_stok:
                        return ['background-color: #fff4cc'] * len(row) # Yellow
                    else:
                        return ['background-color: #ccffcc'] * len(row) # Green
                except:
                    return [''] * len(row)

            st.dataframe(
                df_inventaris.style.apply(highlight_stock, axis=1),
                use_container_width=True
            )
            
            # Alert for low stock
            low_stock = df_inventaris[df_inventaris["Stok"] <= df_inventaris["Min Stok"]]
            if not low_stock.empty:
                st.warning(f"PERINGATAN: {len(low_stock)} barang stok menipis/habis!")
                for _, row in low_stock.iterrows():
                    st.write(f"- **{row['Nama Barang']}**: Sisa {row['Stok']} {row['Satuan']}")
        else:
            st.info("Belum ada data inventaris.")

    with tab2:
        st.subheader("Update / Tambah Barang")
        
        action = st.radio("Aksi", ["Update Stok", "Tambah Barang Baru"], horizontal=True)
        
        if action == "Update Stok":
            df_inventaris = load_data("Inventaris_Barang")
            if not df_inventaris.empty:
                barang_list = df_inventaris["Nama Barang"].tolist()
                selected_barang = st.selectbox("Pilih Barang", barang_list)
                
                # Get current info
                current_row = df_inventaris[df_inventaris["Nama Barang"] == selected_barang].iloc[0]
                st.info(f"Stok Saat Ini: {current_row['Stok']} {current_row['Satuan']}")
                
                update_type = st.radio("Jenis Update", ["Tambah (+)", "Kurang (-)"], horizontal=True)
                jumlah = st.number_input("Jumlah", min_value=1, value=1)
                
                if st.button("Simpan Update"):
                    # Logic to update specific cell would be ideal, but for now we append a new row? 
                    # No, for inventory we must UPDATE the existing row.
                    # Since our save_data appends, we need a new helper or modify logic.
                    # For simplicity in this iteration: We will read all, modify, and OVERWRITE the sheet?
                    # Overwriting is risky with concurrent users.
                    # Better: Use a specific update function using gspread's cell update.
                    
                    # Let's implement a direct update here for now
                    conn = get_connection()
                    if conn:
                        try:
                            ws = conn.worksheet("Inventaris_Barang")
                            cell = ws.find(selected_barang)
                            if cell:
                                # Stok is col 3
                                current_stok = int(current_row['Stok'])
                                new_stok = current_stok + jumlah if update_type == "Tambah (+)" else current_stok - jumlah
                                if new_stok < 0:
                                    st.error("Stok tidak bisa negatif!")
                                else:
                                    ws.update_cell(cell.row, 3, new_stok)
                                    ws.update_cell(cell.row, 6, datetime.now().strftime("%Y-%m-%d %H:%M:%S")) # Update timestamp
                                    st.success(f"Stok {selected_barang} berhasil diupdate menjadi {new_stok}!")
                                    time.sleep(1)
                                    st.rerun()
                        except Exception as e:
                            st.error(f"Gagal update: {e}")
            else:
                st.warning("Data kosong.")
                
        elif action == "Tambah Barang Baru":
            with st.form("form_barang_baru"):
                nama_barang = st.text_input("Nama Barang")
                kategori = st.selectbox("Kategori", ["Kebersihan", "ATK", "Pantry", "Lainnya"])
                stok_awal = st.number_input("Stok Awal", min_value=0)
                satuan = st.text_input("Satuan (misal: Botol, Pack)")
                min_stok = st.number_input("Minimum Stok (Alert)", min_value=1)
                
                if st.form_submit_button("Simpan Barang Baru"):
                    if nama_barang and satuan:
                        data = pd.DataFrame({
                            "Nama Barang": [nama_barang],
                            "Kategori": [kategori],
                            "Stok": [stok_awal],
                            "Satuan": [satuan],
                            "Min Stok": [min_stok],
                            "Terakhir Update": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
                        })
                        if save_data("Inventaris_Barang", data):
                            st.success("Barang baru berhasil ditambahkan!")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.error("Nama barang dan satuan wajib diisi.")

elif menu == "Manajemen Inventaris":
    st.header("Manajemen Inventaris (OfficeOps)")
    
    tab1, tab2 = st.tabs(["Stok Barang", "Update Stok"])
    
    with tab1:
        st.subheader("Daftar Stok Barang")
        df_inventaris = load_data("Inventaris_Barang")
        
        if not df_inventaris.empty:
            # Convert numeric columns
            if "Stok" in df_inventaris.columns:
                df_inventaris["Stok"] = pd.to_numeric(df_inventaris["Stok"], errors='coerce').fillna(0)
            if "Min Stok" in df_inventaris.columns:
                df_inventaris["Min Stok"] = pd.to_numeric(df_inventaris["Min Stok"], errors='coerce').fillna(0)
            
            # Styling function
            def highlight_stock(row):
                try:
                    stok = float(row["Stok"])
                    min_stok = float(row["Min Stok"])
                    if stok == 0:
                        return ['background-color: #ffcccc'] * len(row) # Red
                    elif stok <= min_stok:
                        return ['background-color: #fff4cc'] * len(row) # Yellow
                    else:
                        return ['background-color: #ccffcc'] * len(row) # Green
                except:
                    return [''] * len(row)

            st.dataframe(
                df_inventaris.style.apply(highlight_stock, axis=1),
                use_container_width=True
            )
            
            # Alert for low stock
            low_stock = df_inventaris[df_inventaris["Stok"] <= df_inventaris["Min Stok"]]
            if not low_stock.empty:
                st.warning(f"PERINGATAN: {len(low_stock)} barang stok menipis/habis!")
                for _, row in low_stock.iterrows():
                    st.write(f"- **{row['Nama Barang']}**: Sisa {row['Stok']} {row['Satuan']}")
        else:
            st.info("Belum ada data inventaris.")

    with tab2:
        st.subheader("Update / Tambah Barang")
        
        action = st.radio("Aksi", ["Update Stok", "Tambah Barang Baru"], horizontal=True)
        
        if action == "Update Stok":
            df_inventaris = load_data("Inventaris_Barang")
            if not df_inventaris.empty:
                barang_list = df_inventaris["Nama Barang"].tolist()
                selected_barang = st.selectbox("Pilih Barang", barang_list)
                
                # Get current info
                current_row = df_inventaris[df_inventaris["Nama Barang"] == selected_barang].iloc[0]
                st.info(f"Stok Saat Ini: {current_row['Stok']} {current_row['Satuan']}")
                
                update_type = st.radio("Jenis Update", ["Tambah (+)", "Kurang (-)"], horizontal=True)
                jumlah = st.number_input("Jumlah", min_value=1, value=1)
                
                if st.button("Simpan Update"):
                    conn = get_connection()
                    if conn:
                        try:
                            ws = conn.worksheet("Inventaris_Barang")
                            cell = ws.find(selected_barang)
                            if cell:
                                # Stok is col 3
                                current_stok = int(current_row['Stok'])
                                new_stok = current_stok + jumlah if update_type == "Tambah (+)" else current_stok - jumlah
                                if new_stok < 0:
                                    st.error("Stok tidak bisa negatif!")
                                else:
                                    ws.update_cell(cell.row, 3, new_stok)
                                    ws.update_cell(cell.row, 6, datetime.now().strftime("%Y-%m-%d %H:%M:%S")) # Update timestamp
                                    st.success(f"Stok {selected_barang} berhasil diupdate menjadi {new_stok}!")
                                    time.sleep(1)
                                    st.rerun()
                        except Exception as e:
                            st.error(f"Gagal update: {e}")
            else:
                st.warning("Data kosong.")
                
        elif action == "Tambah Barang Baru":
            with st.form("form_barang_baru"):
                nama_barang = st.text_input("Nama Barang")
                kategori = st.selectbox("Kategori", ["Kebersihan", "ATK", "Pantry", "Lainnya"])
                stok_awal = st.number_input("Stok Awal", min_value=0)
                satuan = st.text_input("Satuan (misal: Botol, Pack)")
                min_stok = st.number_input("Minimum Stok (Alert)", min_value=1)
                
                if st.form_submit_button("Simpan Barang Baru"):
                    if nama_barang and satuan:
                        data = pd.DataFrame({
                            "Nama Barang": [nama_barang],
                            "Kategori": [kategori],
                            "Stok": [stok_awal],
                            "Satuan": [satuan],
                            "Min Stok": [min_stok],
                            "Terakhir Update": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
                        })
                        if save_data("Inventaris_Barang", data):
                            st.success("Barang baru berhasil ditambahkan!")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.error("Nama barang dan satuan wajib diisi.")

elif menu == "Absensi PPNPN":
    st.header("Absensi PPNPN")
    
    # Removed st.form to allow immediate feedback from camera_input
    c1, c2 = st.columns(2)
    nama_pegawai = c1.selectbox("Nama Pegawai", ["Budi", "Siti", "Asep", "Dewi"])
    status_kehadiran = c2.radio("Status", ["Hadir", "Izin", "Sakit"], horizontal=True)
    keterangan = st.text_input("Keterangan (Opsional)")
    
    st.write("Bukti Kehadiran (Wajib Foto Selfie)")
    # Camera input triggers a rerun when photo is taken
    foto_selfie = st.camera_input("Ambil Foto Selfie")
    
    if foto_selfie:
        st.success("Foto berhasil diambil!")
    
    submitted_absen = st.button("Kirim Absen")
    
    if submitted_absen:
        if foto_selfie:
            foto_path = save_uploaded_file(foto_selfie)
            waktu_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            data = pd.DataFrame({
                "Waktu": [waktu_sekarang],
                "Nama Pegawai": [nama_pegawai],
                "Status": [status_kehadiran],
                "Keterangan": [keterangan if keterangan else "-"],
                "Bukti Foto": [foto_path]
            })
            
            if save_data("Presensi_PPNPN", data):
                st.success(f"Absensi {nama_pegawai} berhasil dikirim!")
                if not debug_mode:
                    time.sleep(1)
                    st.rerun()
        else:
            st.error("Wajib mengambil foto selfie untuk absen! Pastikan Anda menekan tombol 'Take Photo'.")

    st.divider()
    st.subheader("Riwayat Absensi Hari Ini")
    
    df_absensi = load_data("Presensi_PPNPN")
    if not df_absensi.empty:
        # Filter for today
        today_str = datetime.now().strftime("%Y-%m-%d")
        # Ensure 'Waktu' column is treated as string/datetime for filtering
        # Assuming format is YYYY-MM-DD HH:MM:SS
        df_absensi["Tanggal_Only"] = df_absensi["Waktu"].astype(str).str.split(" ").str[0]
        df_today = df_absensi[df_absensi["Tanggal_Only"] == today_str].drop(columns=["Tanggal_Only"])
        
        if not df_today.empty:
            # Prepare display dataframe with images
            df_display = df_today.copy()
            if "Bukti Foto" in df_display.columns:
                df_display["Bukti Foto"] = df_display["Bukti Foto"].apply(get_image_data_url)

            st.dataframe(
                df_display,
                use_container_width=True,
                column_config={
                    "Bukti Foto": st.column_config.ImageColumn("Bukti Foto", help="Foto Selfie")
                }
            )
        else:
            st.info("Belum ada data absensi hari ini.")
    else:
        st.info("Belum ada data absensi.")
