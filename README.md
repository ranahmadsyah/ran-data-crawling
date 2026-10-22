# Integrity Content Export

Aplikasi Streamlit untuk mengambil satu halaman dari empat website Integrity melalui API GraphQL yang sudah tersedia, lalu mengunduhnya sebagai Word `.docx`.

## Menjalankan di komputer

Gunakan Python 3.11 atau lebih baru:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

Di macOS/Linux, ganti `.\.venv\Scripts\python.exe` dengan `.venv/bin/python`.

## Deploy ke Streamlit Community Cloud

1. Masukkan `streamlit_app.py`, `integrity_api.py`, `word_export.py`, `requirements.txt`, dan folder `.streamlit` ke repository GitHub.
2. Di Streamlit Community Cloud, pilih **Create app**, pilih repository/branch, dan isi **Main file path** dengan `streamlit_app.py`.
3. Pilih Python 3.13 pada pengaturan lanjutan, lalu deploy.

API publik yang dipakai tidak membutuhkan `.env`, username, atau password. File CSV, dokumen Word lokal, dan skrip scraper lama tidak diperlukan untuk deployment. Jangan upload `.env` atau folder `.venv`.

## Cara pakai

Masukkan URL artikel atau halaman layanan, tekan **Buat dokumen Word**, lalu **Unduh dokumen Word**. Pratinjau menampilkan metadata dan teks konten. **Hapus hasil** menyediakan konfirmasi di tempat. Hasil hanya disimpan dalam memori sesi pengguna, bukan daftar atau file di server.

| Website | API |
| --- | --- |
| integrity-indonesia.com | https://cms-corporate.integrity-asia.com/id/graphql |
| integrity-malaysia.com | https://cms-corporate.integrity-asia.com/ms/graphql |
| integrity-thailand.com | https://cms-corporate.integrity-asia.com/th/graphql |
| integrity-asia.com | https://cms-corporate.integrity-asia.com/asia/graphql |

Bahasa mengikuti awalan URL, misalnya `/id/` dan `/th/`. URL tanpa awalan bahasa memakai bahasa Inggris. Aplikasi tidak menerjemahkan atau menulis ulang konten.

Dokumen mengikuti contoh: tabel **Title tag**, **Meta description**, **URL**, dan **Keyword utama (focus keyword)** di atas, lalu judul dan konten asli di bawah. Tidak ada field Meta keywords. Focus keyword dibaca dari `seo.focuskw`; tidak ditebak dari judul. Nilai metadata kosong ditulis **Kosong**. Konten artikel dibaca dari `content`; halaman layanan juga mengambil `integrityPageTitle` dan `customFields`.

Jika API tidak menyediakan isi halaman, aplikasi memberitahukan **Konten: Kosong**. Jika URL/bahasa tidak ditemukan, aplikasi menampilkan kesalahan dan tidak memakai bahasa lain sebagai pengganti. Halaman yang hanya tersusun di frontend mungkin tidak mempunyai isi di API. Ekspor mencakup konten yang tersedia di API, bukan menu, header, footer, atau teks antarmuka yang ditambahkan frontend. Karakter rusak pada sumber tidak dikoreksi otomatis. Gambar diambil dari empat domain tersebut atau CMS bersama; kegagalan gambar diberitahukan tanpa menggagalkan teks dokumen.

## Pemeriksaan

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Pengujian memakai data tiruan dan tidak mengubah data website.
