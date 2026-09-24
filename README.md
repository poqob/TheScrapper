# TheScrapper

TheScrapper is a versatile web scraping tool designed to extract emails, phone numbers, and social media accounts from
websites. You can use the gathered information for various purposes, such as further research or contacting the
website's owners.

## Installation & Setup

1. Clone the repository:
```bash
git clone https://github.com/champmq/TheScrapper.git
```

2. Change the directory:
```bash
cd TheScrapper
```

3. Install all the requirements:
```bash
pip3 install -r requirements.txt
```

## Web UI

A browser-based interface is available. It supports single URL scraping and batch scraping from CSV or Excel files,
with a live progress bar and direct download of results.
```bash
streamlit run app.py
```

## CLI Usage

- Simple scan:
```bash
python3 TheScrapper.py --url URL
```

- Scan and crawl found URLs:
```bash
python3 TheScrapper.py --url URL --crawl
```

- Retrieve more information about found social media accounts:
```bash
python3 TheScrapper.py --url URL --social-extract
```

- Scrape from a CSV or Excel file:
```bash
python3 TheScrapper.py --csv targets.csv
python3 TheScrapper.py --csv targets.xlsx --csv-column website
```

- Enrich an existing Excel file (e.g. a Google Maps leads export) by scraping
  each website for phone numbers and e-mails:
```bash
python3 TheScrapper.py --scan leads.xlsx
python3 TheScrapper.py --scan leads.xlsx --crawl 2 -t 8
python3 TheScrapper.py --scan leads.xlsx --scan-column url
```

  `--scan` auto-detects the website column (English and Turkish names such as
  `website`, `url`, `link`, `web sitesi`, ...), crawls every listed site and
  appends two new columns — `phone-scan` and `mail-scan` — to a copy of your
  file saved as `output/<filename>-scanned.xlsx`. All original columns and rows
  are preserved; rows without a website are left untouched. Use `--crawl N` to
  also scan up to N linked pages per site (often needed to reach a iletisim/contact page).

Results are automatically written to `output/<filename>_results.csv` or `.xlsx`.


For all available flags:
```bash
python3 TheScrapper.py --help
```

## Adding More Social Media Sites

If you wish to add more social media sites for scraping, you can do so by appending them to the `socials.txt` file.
Feel free to contribute by submitting a pull request if you'd like to share your additions with the community.

### LICENSE - [GNU](LICENSE)
