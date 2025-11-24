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

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# Sidebar
with st.sidebar:
    st.title("Menu")
    menu = st.radio("Pilih Menu", ["Beranda", "Kerumahtanggaan", "Absensi PPNPN"])
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

    # Display metrics
    col1, col2 = st.columns(2)
    col1.metric("Total Laporan Kerusakan", total_kerusakan)
    col2.metric("Total Checklist Kebersihan", total_checklist)

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
            # Prepare display dataframe with images
            df_display = df_kerusakan.copy()
            if "Bukti Foto" in df_display.columns:
                df_display["Bukti Foto"] = df_display["Bukti Foto"].apply(get_image_data_url)

            st.dataframe(
                df_display, 
                use_container_width=True,
                column_config={
                    "Bukti Foto": st.column_config.ImageColumn("Bukti Foto", help="Bukti Foto Laporan")
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
        df_checklist = load_data("Checklist_Kebersihan")
        if not df_checklist.empty:
            # Prepare display dataframe with images
            df_display = df_checklist.copy()
            if "Bukti Foto" in df_display.columns:
                df_display["Bukti Foto"] = df_display["Bukti Foto"].apply(get_image_data_url)

            st.dataframe(
                df_display, 
                use_container_width=True,
                column_config={
                    "Bukti Foto": st.column_config.ImageColumn("Bukti Foto", help="Bukti Foto Kebersihan")
                }
            )
            
            st.download_button(
                label="Download Excel",
                data=to_excel(df_checklist),
                file_name=f"Checklist_Kebersihan_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("Belum ada data checklist.")




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
