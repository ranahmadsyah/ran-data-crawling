"""Streamlit entry point: URL -> source metadata/content -> downloadable Word."""

from html import escape
import logging

import streamlit as st
from bs4 import BeautifulSoup

from integrity_api import ExportError, SITES, fetch_page
from word_export import MIME, build_docx, filename


st.set_page_config(page_title="Integrity · Content Export", page_icon="📄", layout="centered")
st.html("""<style>
.stMainBlockContainer {max-width: 860px; padding-top: 5rem; padding-bottom: 3rem;}
.brand {font-size:.75rem; letter-spacing:.16em; font-weight:700; color:#14675b; margin-bottom:1rem;}
.intro {color:#64746b; font-size:1.05rem; margin-bottom:1.4rem;}
.sites {display:flex; gap:.5rem; flex-wrap:wrap; margin-bottom:1.6rem;}
.sites span {border:1px solid #dce4dc; border-radius:20px; padding:.3rem .7rem; font-size:.78rem; color:#4a6257;}
h1 {font-size:2.6rem!important; line-height:1.15!important; letter-spacing:-.04em;}
.metadata {margin:.8rem 0 1.3rem; padding:0!important;}
.metadata div {display:grid; grid-template-columns:180px minmax(0,1fr); gap:1rem; padding:.8rem 0; border-bottom:1px solid #e2e8e0;}
.metadata dt {color:#64746b; font-size:.85rem;}
.metadata dd {margin:0; overflow-wrap:anywhere; font-size:.9rem;}
.preview {overflow-wrap:anywhere; line-height:1.7;}
.preview h1,.preview h2 {font-size:1.35rem!important; margin-top:1.5rem;}
.preview h3 {font-size:1.1rem;}
.preview table {width:100%; table-layout:fixed; border-collapse:collapse;}
.preview td,.preview th {border:1px solid #dce4dc; padding:.5rem; overflow-wrap:anywhere;}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius:16px;}
@media (max-width:600px) {
 .stMainBlockContainer {padding:4.5rem 1rem 1.5rem;}
 h1 {font-size:2rem!important;}
 .metadata div {grid-template-columns:minmax(0,1fr); gap:.25rem;}
 [data-testid="stHorizontalBlock"] {flex-direction:column;}
 [data-testid="stColumn"] {width:100%!important; flex:1 1 100%!important; min-width:0!important;}
}
</style>""")


def clear_result():
    st.session_state.pop("result", None)
    st.session_state.pop("confirm_clear", None)


def preview_html(content):
    soup = BeautifulSoup(content, "html.parser")
    allowed = {"p", "br", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li",
               "strong", "b", "em", "i", "blockquote", "table", "tbody", "thead", "tr", "td", "th"}
    for tag in list(soup.find_all(True)):
        if tag.parent is None:
            continue
        if tag.name in {"script", "style", "noscript", "img", "iframe"}:
            tag.decompose()
        elif tag.name not in allowed:
            tag.unwrap()
        else:
            tag.attrs = {}
    return '<div class="preview">' + str(soup) + '</div>'


st.html('<div class="brand">INTEGRITY / CONTENT EXPORT</div>')
st.title("Dari URL ke dokumen Word.")
st.html('<p class="intro">Masukkan URL halaman Integrity. Ambil konten aslinya, lalu unduh dokumen yang siap digunakan.</p>')
st.html('<div class="sites">' + ''.join(f'<span>{escape(name)}</span>' for name, _ in SITES.values()) + '</div>')

with st.form("export_form", border=True):
    url = st.text_input("URL halaman", key="page_url", placeholder="https://www.integrity-indonesia.com/id/blog/…")
    st.caption("Mendukung artikel dan halaman layanan. Bahasa mengikuti URL yang dimasukkan.")
    submitted = st.form_submit_button("Buat dokumen Word", type="primary", width="stretch")

if submitted:
    clear_result()
    try:
        with st.spinner("Mengambil konten dan menyiapkan dokumen…"):
            page = fetch_page(url)
            document, warnings = build_docx(page)
            st.session_state.result = {"page": page, "document": document, "warnings": warnings}
    except ExportError as exc:
        st.error(str(exc))
    except Exception:
        logging.exception("Word export failed")
        st.error("Dokumen belum berhasil dibuat. Coba lagi atau gunakan URL halaman lain.")

result = st.session_state.get("result")
if result:
    page = result["page"]
    with st.container(border=True):
        st.success("Dokumen siap diunduh.")
        st.subheader(page.title or "Judul: Kosong")
        st.caption(f"{page.site} · {page.language.upper()} · Word (.docx)")
        st.html('<dl class="metadata">' + ''.join(
            f'<div><dt>{escape(label)}</dt><dd>{escape(value)}</dd></div>' for label, value in page.metadata) + '</dl>')
        for warning in page.warnings + result["warnings"]:
            st.warning(warning)
        st.download_button("Unduh dokumen Word", result["document"], file_name=filename(page),
                           mime=MIME, type="primary", width="stretch", on_click="ignore")
        with st.expander("Pratinjau konten"):
            if BeautifulSoup(page.content, "html.parser").get_text(strip=True):
                st.html(preview_html(page.content))
            else:
                st.info("Konten: Kosong")
            st.caption("Gambar yang berhasil diambil disertakan dalam dokumen Word.")
        if st.button("Hapus hasil", key="clear_result", width="stretch"):
            st.session_state.confirm_clear = True
        if st.session_state.get("confirm_clear"):
            st.warning("Hapus hasil dan dokumen dari sesi ini?")
            confirm, cancel = st.columns(2)
            confirm.button("Ya, hapus hasil", key="confirm_delete", on_click=clear_result, width="stretch")
            cancel.button("Batal", key="cancel_delete", on_click=lambda: st.session_state.pop("confirm_clear", None), width="stretch")
else:
    st.caption("01 Masukkan URL  →  02 Buat dokumen  →  03 Unduh Word")

st.caption("Metadata dipisahkan dari konten. Field yang kosong ditandai “Kosong”, tanpa menambahkan data baru.")
