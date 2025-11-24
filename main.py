import streamlit as st
import pandas as pd
import os
import io
import gspread
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

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# Sidebar
with st.sidebar:
    st.title("Menu")
    menu = st.radio("Pilih Menu", ["Beranda", "Kerumahtanggaan", "Humas", "Absensi PPNPN"])
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
    df_checklist = load_data("Checklist_Kebersihan")
    df_konten = load_data("Rencana_Konten")

    # Calculate metrics
    total_kerusakan = len(df_kerusakan) if not df_kerusakan.empty else 0
    total_checklist = len(df_checklist) if not df_checklist.empty else 0
    
    if not df_konten.empty and "Status" in df_konten.columns:
        total_ide = len(df_konten[df_konten["Status"] == "Ide"])
    else:
        total_ide = 0

    # Display metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Laporan Kerusakan", total_kerusakan)
    col2.metric("Total Checklist Kebersihan", total_checklist)
    col3.metric("Rencana Konten 'Ide'", total_ide)

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
    tab1, tab2 = st.tabs(["Laporan Kerusakan", "Kontrol PPNPN"])

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
                    foto_path = save_uploaded_file(uploaded_foto)
                    data = pd.DataFrame({
                        "Tanggal": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                        "Nama Pelapor": [nama_pelapor],
                        "Lokasi": [lokasi],
                        "Kendala": [kendala],
                        "Bukti Foto": [foto_path if foto_path else "-"]
                    })
                    if save_data("Laporan_Kerusakan", data):
                        st.success("Laporan berhasil dikirim!")
                        if not debug_mode:
                            time.sleep(1)
                            st.rerun()
                else:
                    st.error("Mohon lengkapi semua field.")
        
        st.divider()
        st.subheader("Riwayat Laporan")
        df_kerusakan = load_data("Laporan_Kerusakan")
        if not df_kerusakan.empty:
            st.dataframe(
                df_kerusakan, 
                use_container_width=True,
                column_config={
                    "Bukti Foto": st.column_config.TextColumn("Bukti Foto", help="Path file foto")
                }
            )
            # Optional: Display images in an expander if user wants to see them
            with st.expander("Lihat Galeri Foto Kerusakan"):
                if "Bukti Foto" in df_kerusakan.columns:
                    cols = st.columns(4)
                    for idx, row in df_kerusakan.iterrows():
                        if row["Bukti Foto"] != "-" and os.path.exists(row["Bukti Foto"]):
                            with cols[idx % 4]:
                                st.image(row["Bukti Foto"], caption=f"{row['Lokasi']} - {row['Tanggal']}", use_container_width=True)
            
            st.download_button(
                label="Download Excel",
                data=to_excel(df_kerusakan),
                file_name=f"Rekapan_Kerusakan_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("Belum ada laporan.")

    with tab2:
        st.subheader("Kontrol PPNPN")
        with st.form("form_ppnpn"):
            c1, c2 = st.columns(2)
            nama_petugas = c1.text_input("Nama Petugas")
            area = c2.selectbox("Area", ["Lobby", "Ruang Rapat", "Toilet", "Pantry", "Halaman"])
            kondisi = st.radio("Kondisi", ["Bersih", "Kotor"])
            uploaded_foto_ppnpn = st.file_uploader("Upload Bukti Foto", type=['png', 'jpg', 'jpeg'])
            submitted_ppnpn = st.form_submit_button("Simpan Checklist")

            if submitted_ppnpn:
                if nama_petugas:
                    foto_path = save_uploaded_file(uploaded_foto_ppnpn)
                    data = pd.DataFrame({
                        "Tanggal": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                        "Nama Petugas": [nama_petugas],
                        "Area": [area],
                        "Kondisi": [kondisi],
                        "Bukti Foto": [foto_path if foto_path else "-"]
                    })
                    if save_data("Checklist_Kebersihan", data):
                        st.success("Checklist berhasil disimpan!")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error("Mohon isi nama petugas.")
        
        st.divider()
        st.subheader("Riwayat Checklist")
        df_ppnpn = load_data("Checklist_Kebersihan")
        if not df_ppnpn.empty:
            st.dataframe(
                df_ppnpn, 
                use_container_width=True,
                column_config={
                    "Bukti Foto": st.column_config.TextColumn("Bukti Foto", help="Path file foto")
                }
            )
             # Optional: Display images in an expander
            with st.expander("Lihat Galeri Foto Kebersihan"):
                if "Bukti Foto" in df_ppnpn.columns:
                    cols = st.columns(4)
                    for idx, row in df_ppnpn.iterrows():
                        if row["Bukti Foto"] != "-" and os.path.exists(row["Bukti Foto"]):
                            with cols[idx % 4]:
                                st.image(row["Bukti Foto"], caption=f"{row['Area']} - {row['Tanggal']}", use_container_width=True)
            
            st.download_button(
                label="Download Excel",
                data=to_excel(df_ppnpn),
                file_name=f"Rekapan_Kebersihan_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("Belum ada data checklist.")

elif menu == "Humas":
    st.header("Humas - Content Planner")
    with st.form("form_content"):
        c1, c2 = st.columns(2)
        tanggal = c1.date_input("Tanggal Posting")
        status = c2.selectbox("Status", ["Ide", "Draft", "Siap Post", "Sudah Post"])
        platform = st.multiselect("Platform", ["Instagram", "TikTok", "Website", "Facebook"])
        caption = st.text_area("Rencana Caption")
        
        submitted_content = st.form_submit_button("Simpan Rencana")

        if submitted_content:
            if caption and platform:
                data = pd.DataFrame({
                    "Tanggal": [str(tanggal)], # Convert date to string for JSON serialization if needed, though gspread handles it
                    "Caption": [caption],
                    "Platform": [", ".join(platform)],
                    "Status": [status]
                })
                if save_data("Rencana_Konten", data):
                    st.success("Rencana konten berhasil disimpan!")
                    time.sleep(1)
                    st.rerun()
            else:
                st.error("Mohon lengkapi caption dan platform.")

    st.divider()
    st.subheader("Daftar Rencana Konten")
    df_content = load_data("Rencana_Konten")
    if not df_content.empty:
        st.dataframe(df_content, use_container_width=True)
        
        st.download_button(
            label="Download Excel",
            data=to_excel(df_content),
            file_name=f"Rencana_Konten_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Belum ada rencana konten.")

elif menu == "Absensi PPNPN":
    st.header("Absensi PPNPN")
    
    with st.form("form_absensi"):
        c1, c2 = st.columns(2)
        nama_pegawai = c1.selectbox("Nama Pegawai", ["Budi", "Siti", "Asep", "Dewi"])
        status_kehadiran = c2.radio("Status", ["Hadir", "Izin", "Sakit"], horizontal=True)
        keterangan = st.text_input("Keterangan (Opsional)")
        
        st.write("Bukti Kehadiran (Wajib Foto Selfie)")
        foto_selfie = st.camera_input("Ambil Foto Selfie")
        
        submitted_absen = st.form_submit_button("Kirim Absen")
        
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
                st.error("Wajib mengambil foto selfie untuk absen!")

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
            st.dataframe(
                df_today,
                use_container_width=True,
                column_config={
                    "Bukti Foto": st.column_config.TextColumn("Bukti Foto", help="Path file foto")
                }
            )
            
            # Gallery for today
            with st.expander("Lihat Foto Absensi Hari Ini"):
                if "Bukti Foto" in df_today.columns:
                    cols = st.columns(4)
                    for idx, row in df_today.iterrows():
                        if row["Bukti Foto"] != "-" and os.path.exists(row["Bukti Foto"]):
                            with cols[idx % 4]:
                                st.image(row["Bukti Foto"], caption=f"{row['Nama Pegawai']} - {row['Waktu']}", use_container_width=True)
        else:
            st.info("Belum ada data absensi hari ini.")
    else:
        st.info("Belum ada data absensi.")
