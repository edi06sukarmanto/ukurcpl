import streamlit as st
import re
import json
from pypdf import PdfReader
import pandas as pd
from io import BytesIO

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Hitung Ketercapaian CPL", page_icon="📊", layout="wide")

st.title("📊 TABEL REKAPITULASI KETERCAPAIAN CPL - SEMESTER GANJIL")
st.caption("Aplikasi berbasis web untuk ekstraksi otomatis capaian pembelajaran dari berkas PDF.")

# --- STATE MANAGEMEN (Pengganti file json lokal / users folder) ---
# Di Streamlit, kita pakai st.session_state agar data tidak hilang saat web di-refresh
if "extracted_rows" not in st.session_state:
    st.session_state.extracted_rows = []

if "cpls_names" not in st.session_state:
    # Default 9 CPL seperti di konfigurasi awal Akang
    st.session_state.cpls_names = [f"CPL{i}" for i in range(1, 10)]

# --- SIDEBAR: KONFIGURASI CPL ---
with st.sidebar:
    st.header("⚙️ Konfigurasi CPL")
    num_cpl = st.number_input("Jumlah CPL:", min_value=1, max_value=20, value=len(st.session_state.cpls_names))
    
    new_names = []
    for i in range(int(num_cpl)):
        default_val = st.session_state.cpls_names[i] if i < len(st.session_state.cpls_names) else f"CPL{i+1}"
        name = st.text_input(f"Nama CPL {i+1}:", value=default_val, key=f"cpl_input_{i}")
        new_names.append(name if name.strip() else f"CPL{i+1}")
        
    if st.button("Simpan & Terapkan Konfigurasi"):
        st.session_state.cpls_names = new_names
        st.success("Konfigurasi CPL berhasil diperbarui!")
        st.rerun()

# --- FUNGSI EKSTRAKSI PDF (Logika asli milik Akang) ---
def extract_course_data_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    semester, kode, nama = "", "", ""
    for i, line in enumerate(lines):
        if "Nama Mata Kuliah" in line and "Kode Mata Kuliah" in line:
            if i + 1 < len(lines):
                course_line = lines[i + 1]
                match = re.match(r'^(.+?)\s+([A-Za-z0-9-]+)\s+\d+\s+(\d+)\s+.+$', course_line)
                if match:
                    nama = match.group(1).strip()
                    kode = match.group(2).strip()
                    semester = match.group(3).strip()
                else:
                    parts = course_line.split()
                    if len(parts) >= 5:
                        nama = " ".join(parts[:-4]).strip()
                        kode = parts[-4].strip()
                        semester = parts[-3].strip()
            break

    cpl_map = {
        "CPL01": 1, "CPL1": 1, "CPL05": 5, "CPL5": 5,
        "CPL02": 2, "CPL2": 2, "CPL06": 6, "CPL6": 6,
        "CPL03": 3, "CPL3": 3, "CPL07": 7, "CPL7": 7,
        "CPL04": 4, "CPL4": 4, "CPL08": 8, "CPL8": 8,
        "CPL09": 9, "CPL9": 9,
        "P01": 5, "P02": 6, "P03": 7, "P04": 8, "P05": 9,
        "KK01": 7, "K01": 7, "KK02": 8, "K02": 8,
        "KU01": 6, "KU02": 7, "KS01": 9, "KS02": 8
    }
    
    cpl_values = {f"CPL{i}": "" for i in range(1, max(9, len(st.session_state.cpls_names)) + 1)}
    
    for i, line in enumerate(lines):
        match = re.match(r'^([A-Z]{1,3}\d{1,2})\s*-', line)
        if match:
            code = match.group(1)
            cpl_num = cpl_map.get(code)
            if cpl_num and cpl_values[f"CPL{cpl_num}"] == "":
                candidates = []
                for j in range(i + 1, min(i + 100, len(lines))):
                    line_text = lines[j].strip()
                    numbers = re.findall(r'\d+\.\d{2}', line_text)
                    if numbers and len(numbers) >= 2 and '%' not in line_text:
                        candidates.append(numbers[1])
                    if re.match(r'^[A-Z]{1,3}\d{2}\s*-', lines[j]):
                        break
                if candidates:
                    cpl_values[f"CPL{cpl_num}"] = candidates[1] if len(candidates) > 1 else candidates[0]

    row = {"semester": semester, "kode": kode, "nama": nama}
    for i in range(1, len(st.session_state.cpls_names) + 1):
        row[f"CPL{i}"] = cpl_values.get(f"CPL{i}", "")
    return row

# --- BAGIAN UPLOAD FILE ---
st.subheader("📁 Unggah Berkas PDF Nilai")
uploaded_files = st.file_uploader("Pilih satu atau beberapa file PDF", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    if st.button("🚀 Ekstrak Data Dari PDF"):
        new_rows = []
        for pdf in uploaded_files:
            try:
                data = extract_course_data_from_pdf(pdf)
                # Validasi duplikasi data berdasarkan semester dan kode MK
                exists = any(r['semester'] == data['semester'] and r['kode'] == data['kode'] for r in st.session_state.extracted_rows)
                if not exists and (data["kode"] or data["nama"]):
                    st.session_state.extracted_rows.append(data)
            except Exception as e:
                st.error(f"Gagal memproses {pdf.name}: {e}")
        st.success("Ekstraksi selesai!")
        st.rerun()

# --- TABEL UTAMA & RINGKASAN ---
if st.session_state.extracted_rows:
    st.write("---")
    st.subheader("📋 Data Hasil Ekstraksi")
    
    # Konversi ke Pandas DataFrame untuk visualisasi tabel yang rapi di Streamlit
    df = pd.DataFrame(st.session_state.extracted_rows)
    
    # Atur susunan kolom agar presisi
    kolom_utama = ['semester', 'kode', 'nama']
    kolom_cpl = [f"CPL{i}" for i in range(1, len(st.session_state.cpls_names) + 1)]
    df = df[kolom_utama + kolom_cpl]
    
    # Rename kolom header sesuai konfigurasi nama CPL dinamis
    rename_dict = {f"CPL{i}": st.session_state.cpls_names[i-1] for i in range(1, len(st.session_state.cpls_names) + 1)}
    df_display = df.rename(columns=rename_dict)
    
    # Tampilkan tabel interaktif
    st.dataframe(df_display, use_container_width=True)
    
    # Tombol Aksi Kontrol Data
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Hitung CPL Gabungan (Logika matematika rata-rata persentase milik Akang)
        if st.button("🧮 Hitung CPL Gabungan"):
            st.info("### 📈 Ringkasan Rata-rata CPL")
            n = len(st.session_state.cpls_names)
            for i in range(1, n+1):
                label = st.session_state.cpls_names[i-1]
                total_val = 0.0
                count = 0
                for row in st.session_state.extracted_rows:
                    val = row.get(f"CPL{i}", "")
                    if val != "":
                        try:
                            total_val += float(val)
                            count += 1
                        except ValueError:
                            continue
                if count > 0:
                    st.write(f"**{label}**: `{total_val / count:.2f}%`")
                else:
                    st.write(f"**{label}**: `-`")
                    
    with col2:
        # Fitur Ekspor langsung via unduhan browser (Tanpa perlu menulis ke harddisk server cloud)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_display.to_excel(writer, index=False, sheet_name="Ekstraksi CPL")
        processed_data = output.getvalue()
        
        st.download_button(
            label="📥 Ekspor Tabel ke Excel",
            data=processed_data,
            file_name="Rekap Ketercapaian CPL - Semester Ganjil.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    with col3:
        if st.button("🗑️ Hapus Semua Data Ekstrak", type="primary"):
            st.session_state.extracted_rows = []
            st.success("Semua data berhasil dibersihkan!")
            st.rerun()
else:
    st.info("Belum ada data hasil ekstraksi. Silakan unggah file PDF di atas.")
