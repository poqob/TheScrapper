import io
import threading
from argparse import Namespace
from pathlib import Path

import streamlit as st
import pandas as pd

from modules.scrapper import Scrapper
from modules.info_reader import InfoReader
from modules.xlsx_scanner import detect_website_column
from TheScrapper import normalize_url, scrape

from concurrent.futures import ThreadPoolExecutor, as_completed
import requests


def scrape_urls(urls: list, args: Namespace, progress_bar, status_text) -> list:
    """Scrape URLs with threads, updating Streamlit progress."""
    results = {}
    total = len(urls)
    completed = 0
    failed = 0
    lock = threading.Lock()

    def _scrape_one(url):
        try:
            return url, scrape(url, args)
        except requests.exceptions.RequestException:
            return url, None

    with ThreadPoolExecutor(max_workers=args.threads) as pool:
        futures = {pool.submit(_scrape_one, url): url for url in urls}
        for future in as_completed(futures):
            url, result = future.result()
            with lock:
                completed += 1
                if result is not None:
                    results[url] = result
                else:
                    failed += 1
                progress_bar.progress(completed / total)
                status_text.text(f"[{completed}/{total}] Done: {completed - failed} | Failed: {failed}")

    return [results[url] for url in urls if url in results]


def results_to_dataframe(results: list) -> pd.DataFrame:
    """Convert scrape results to a pandas DataFrame."""
    rows = []
    for r in results:
        rows.append({
            "URL": r.get("Target", ""),
            "Emails": "; ".join(r.get("E-Mails", [])),
            "Phone Numbers": "; ".join(r.get("Numbers", [])),
            "Social Media": "; ".join(r.get("SocialMedia", [])),
        })
    return pd.DataFrame(rows)


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    """Convert DataFrame to Excel bytes for download."""
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    return buf.getvalue()


# --- Page config ---
st.set_page_config(page_title="TheScrapper", page_icon="🔍", layout="wide")

st.markdown(
    "<h1 style='text-align: center;'>TheScrapper</h1>"
    "<p style='text-align: center; color: gray;'>Extract emails, phone numbers & social media links from websites</p>",
    unsafe_allow_html=True,
)

st.divider()

# --- Sidebar: Options ---
with st.sidebar:
    st.header("Options")

    st.subheader("Extract")
    extract_emails = st.checkbox("Emails", value=True)
    extract_numbers = st.checkbox("Phone Numbers", value=True)
    extract_socials = st.checkbox("Social Media", value=True)

    st.subheader("Settings")
    crawl = st.checkbox("Crawl links on each page", value=False)
    crawl_pages = st.number_input("Max crawled links", min_value=1, value=2, step=1, disabled=not crawl)
    crawl_external = st.checkbox("Include external links while crawling", value=False, disabled=not crawl)
    threads = st.slider("Threads", min_value=1, max_value=50, value=10)

# Build a fake Namespace matching what scrape() expects
args = Namespace(
    email=extract_emails and not (extract_emails and extract_numbers and extract_socials),
    number=extract_numbers and not (extract_emails and extract_numbers and extract_socials),
    socials=extract_socials and not (extract_emails and extract_numbers and extract_socials),
    social_extract=False,
    crawl=int(crawl_pages) if crawl else 0,
    crawl_external=crawl_external if crawl else False,
    threads=threads,
)
# If all three are checked, set all to False so scrape() defaults to extracting everything
if extract_emails and extract_numbers and extract_socials:
    args.email = False
    args.number = False
    args.socials = False

# --- Input ---
tab_single, tab_batch = st.tabs(["Single URL", "Batch (CSV / Excel)"])

with tab_single:
    url_input = st.text_input("Enter a URL", placeholder="https://example.com")
    run_single = st.button("Scrape", key="single", use_container_width=True)

with tab_batch:
    uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx", "xls"])
    col_name = st.text_input("Column name containing URLs", value="", placeholder="Leave empty to auto-detect")
    run_batch = st.button("Scrape All", key="batch", use_container_width=True)

# --- Processing ---

if run_single and url_input:
    url = normalize_url(url_input.strip())
    with st.spinner(f"Scraping {url}..."):
        try:
            result = scrape(url, args)
        except requests.exceptions.RequestException as e:
            st.error(f"Failed to scrape: {e}")
            st.stop()

    st.success("Done!")
    df = results_to_dataframe([result])
    st.dataframe(df, use_container_width=True, hide_index=True)

    # --- Export ---
    st.subheader("Export")
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "Download CSV",
            df.to_csv(index=False).encode("utf-8"),
            file_name="result.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            "Download Excel",
            to_excel_bytes(df),
            file_name="result.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

elif run_batch and uploaded_file:
    # Read URLs from uploaded file
    try:
        if uploaded_file.name.endswith((".xlsx", ".xls")):
            input_df = pd.read_excel(uploaded_file, engine="openpyxl")
        else:
            input_df = pd.read_csv(uploaded_file)
    except Exception as e:
        st.error(f"Could not read file: {e}")
        st.stop()

    if not col_name or col_name not in input_df.columns:
        col_name = detect_website_column(input_df.columns.tolist(), input_df.values.tolist())
        if col_name is None:
            st.error(
                "Could not auto-detect a website column. Available columns: "
                + ", ".join(input_df.columns),
            )
            st.stop()
        st.success(f"Auto-detected website column: **'{col_name}'**")

    raw_urls = input_df[col_name].dropna().astype(str).str.strip().tolist()
    raw_urls = [u for u in raw_urls if u]

    if not raw_urls:
        st.warning("No URLs found in the specified column.")
        st.stop()

    urls = [normalize_url(u) for u in raw_urls]

    st.info(f"Scraping **{len(urls)}** URLs with **{threads}** threads...")
    progress_bar = st.progress(0)
    status_text = st.empty()

    results = scrape_urls(urls, args, progress_bar, status_text)

    st.success(f"Completed! {len(results)}/{len(urls)} URLs scraped successfully.")

    # Enrich the original file with the scraped contact data.
    results_map = {r.get("Target", ""): r for r in results}

    def scan_columns(value):
        if value is None or not str(value).strip():
            return "", ""
        r = results_map.get(normalize_url(str(value).strip()))
        if not r:
            return "", ""
        return "; ".join(r.get("Numbers", [])), "; ".join(r.get("E-Mails", []))

    enriched = input_df.copy()
    enriched["phone-scan"], enriched["mail-scan"] = zip(*enriched[col_name].apply(scan_columns))
    st.dataframe(enriched, use_container_width=True, hide_index=True)

    # --- Export ---
    st.subheader("Export")
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "Download CSV",
            enriched.to_csv(index=False).encode("utf-8"),
            file_name="results-scanned.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            "Download Excel",
            to_excel_bytes(enriched),
            file_name=f"{uploaded_file.name.split('.')[0]}-scanned.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
