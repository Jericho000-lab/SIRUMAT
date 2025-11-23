import streamlit as st
import pandas as pd
import os
import io
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

def load_data(filepath):
    if not os.path.exists(filepath):
        return pd.DataFrame()
    return pd.read_csv(filepath)

def save_data(filepath, new_data):
    if not os.path.exists(filepath):
        new_data.to_csv(filepath, index=False)
    else:
        new_data.to_csv(filepath, mode='a', header=False, index=False)

# Sidebar
with st.sidebar:
    st.title("Menu")
    menu = st.radio("Pilih Menu", ["Beranda", "Kerumahtanggaan", "Humas"])

# Main content
st.title("Si-Rumat")

if menu == "Beranda":
    st.header("Dashboard Statistik")
    
    # Load data for metrics
    df_kerusakan = load_data("laporan_kerusakan.csv")
    df_checklist = load_data("checklist_kebersihan.csv")
    df_konten = load_data("rencana_konten.csv")

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
                    save_data("laporan_kerusakan.csv", data)
                    st.success("Laporan berhasil dikirim!")
                    st.rerun()
                else:
                    st.error("Mohon lengkapi semua field.")
        
        st.divider()
        st.subheader("Riwayat Laporan")
        df_kerusakan = load_data("laporan_kerusakan.csv")
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
                    save_data("checklist_kebersihan.csv", data)
                    st.success("Checklist berhasil disimpan!")
                    st.rerun()
                else:
                    st.error("Mohon isi nama petugas.")
        
        st.divider()
        st.subheader("Riwayat Checklist")
        df_ppnpn = load_data("checklist_kebersihan.csv")
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
                    "Tanggal": [tanggal],
                    "Caption": [caption],
                    "Platform": [", ".join(platform)],
                    "Status": [status]
                })
                save_data("rencana_konten.csv", data)
                st.success("Rencana konten berhasil disimpan!")
                st.rerun()
            else:
                st.error("Mohon lengkapi caption dan platform.")

    st.divider()
    st.subheader("Daftar Rencana Konten")
    df_content = load_data("rencana_konten.csv")
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
