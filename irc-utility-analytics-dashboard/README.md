# IRC Utility Operations Dashboard V6

Streamlit dashboard for dialysis-center utility analytics.

## Included pages

1. Operations Command Center
2. Exception Center
3. Property Scorecard
4. Geographic View
5. Monthly Summary Report with one-page PDF export

There is no raw Data Explorer page.

## Live Google Sheet

This repo is already configured in `config.py` with the Google Sheet shared in the conversation:

```python
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1_4coHOmEkzY9cLYRtqmnUJ51LuqeY6yz/edit?gid=910919948#gid=910919948"
```

The app reads the Google Sheet live and auto-refreshes every 30 seconds.

## Password

The default password in `config.py` is:

```text
ChangeMeUtility2026!
```

Change it before sharing the dashboard, or set it in Streamlit Cloud Secrets:

```toml
APP_PASSWORD = "your-real-password-here"
```

## Key updates in this version

- Dark design on all pages with light-mode toggle
- Password protection
- Sticky/frozen top filters
- Multi-select filters with `All` option
- No raw spreadsheet-looking tables
- No horizontal table scrolling
- Missing bill logic changed:
  - flags only when the selected month has no bill for that property + utility
  - displays `Latest month on file: Month YYYY`
- Geographic View:
  - property counts by state
  - property dots on the U.S. map
  - dots colored by status: Normal, Review, Critical
  - uses Latitude/Longitude if present; otherwise uses Street + City + State + Zip Code geocoding with cache/fallback
- Monthly Summary Report PDF export

## Deploy to Streamlit Cloud

1. Upload the contents of this folder to GitHub.
2. Go to Streamlit Community Cloud.
3. Create a new app from the repo.
4. Main file path:

```text
app.py
```

5. Optional but recommended: set `APP_PASSWORD` in Streamlit Secrets.

## Notes about the map

The sheet already has:

- Property Name
- Street
- City
- State
- Zip Code

The app can geocode property addresses from those fields. For best and fastest exact dots, add these optional columns to the Google Sheet later:

- Latitude
- Longitude

If those columns exist, the app will use them directly.
