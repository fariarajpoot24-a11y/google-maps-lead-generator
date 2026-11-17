# Google Maps Lead Generator

A Flask-based web application that scrapes public business listings from Google Maps using Playwright and exports results to CSV or Excel.

## Features

- Scrape public Google Maps business listings.
- No Google Maps API key required.
- Headless browser automation using Playwright.
- Extract business information.
- Automatically remove duplicate results.
- Export results to CSV and Excel.
- Simple web dashboard.
- Configurable scraping settings.

## Tech Stack

- Python 3.11.9
- Flask
- Playwright
- HTML, CSS, JavaScript
- Pandas / Excel export

## Project Structure

```text
google-maps-lead-generator/
│
├── app.py
├── scraper.py
├── export.py
├── requirements.txt
├── .python-version
├── .gitignore
│
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── script.js
│
└── templates/
    └── index.html
```

## Local Installation

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd google-maps-lead-generator
```

### 2. Create virtual environment

Windows:

```powershell
python -m venv venv
venv\Scripts\activate
```

macOS / Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright Chromium

```bash
playwright install chromium
```

### 5. Run the application

```bash
python app.py
```

Open in your browser:

```text
http://127.0.0.1:5000
```

## Deploy on Render

### 1. Push project to GitHub

Upload your project to a GitHub repository.

### 2. Create Render Web Service

- Open https://render.com
- Select New → Web Service.
- Connect your GitHub repository.
- Select Python as the runtime.

### 3. Build Command

```bash
pip install -r requirements.txt && playwright install chromium
```

### 4. Start Command

```bash
gunicorn app:app --bind 0.0.0.0:$PORT --timeout 900 --workers 1
```

### 5. Environment Variables

Configure these variables in Render:

| Key | Value |
|---|---|
| PYTHON_VERSION | 3.11.9 |
| PLAYWRIGHT_BROWSERS_PATH | 0 |
| HEADLESS | true |
| MAX_CONCURRENCY | 2 |

### 6. Deploy

Click Deploy and wait for the build to complete.

**Important:** Chromium may require additional system libraries on Render. Google Maps may also display CAPTCHA or block automated requests.

## Troubleshooting

**No results returned**
- Check whether Google Maps is displaying CAPTCHA.
- Try running with `HEADLESS=false` locally.

**Business fields are missing**
- Google Maps may have changed its HTML structure.
- Update the CSS selectors in the `SELECTORS` dictionary inside `scraper.py`.

**Deployment errors**
- Check Render build logs.
- Verify Playwright and Chromium installation.
- Ensure environment variables are configured correctly.

## Important Notice

Scraping Google Maps may be subject to Google's Terms of Service. Respect privacy, applicable laws, and anti-spam requirements.

---

**Google Maps Lead Generator**