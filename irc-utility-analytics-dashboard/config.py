"""Dashboard configuration.

This repo is configured to read the Google Sheet shared in the conversation.
For stronger security in production, move APP_PASSWORD and/or GOOGLE_SHEET_URL
into Streamlit Cloud Secrets.
"""

APP_TITLE = "IRC Utility Operations"

GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1_4coHOmEkzY9cLYRtqmnUJ51LuqeY6yz/edit?gid=910919948#gid=910919948"
GOOGLE_SHEET_ID = "1_4coHOmEkzY9cLYRtqmnUJ51LuqeY6yz"
GOOGLE_SHEET_GID = "910919948"
GOOGLE_WORKSHEET = "Property"

AUTO_REFRESH_SECONDS = 30

# Change this before sharing the deployed app, or set APP_PASSWORD in Streamlit Secrets.
APP_PASSWORD = "ChangeMeUtility2026!"

# Alert thresholds.
WARNING_THRESHOLD = 10.0
CRITICAL_THRESHOLD = 20.0
FLAT_CHANGE_TOLERANCE = 5.0

# Geographic view.
# If Latitude/Longitude columns are added to the sheet later, the app will use them.
# Otherwise it will try to geocode Street + City + State + Zip Code and cache results.
GEOCODE_ADDRESSES = True
MAX_GEOCODES_PER_RUN = 250

REPORT_TITLE = "Monthly Utility Summary Report"
REPORT_SUBTITLE = "Dialysis Center Utility Portfolio"
