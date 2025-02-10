import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from dotenv import load_dotenv
from tensorflow.python.data.kernel_tests.test_base import v1_only_combinations

load_dotenv()
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = "11_bSt65saR_i9z-2ecDgJPVoYl4_kZ51Nj6kti-nipQ"
SAMPLE_RANGE_NAME = "sheet1!A1:M"
SPREADSHEET_CREDENTIAL_PATH = os.getenv("SPREADSHEET_CREDENTIAL_PATH")


def get_spreadsheet_data() -> list[list[str]]:
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                SPREADSHEET_CREDENTIAL_PATH, SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    service = build("sheets", "v4", credentials=creds)
    sheet = service.spreadsheets()
    result = (
        sheet.values()
        .get(spreadsheetId=SAMPLE_SPREADSHEET_ID, range=SAMPLE_RANGE_NAME)
        .execute()
    )
    values = result.get("values", [])
    if not values:
        raise Exception("No data found. [get_spreadsheet_data]")
    return values


def get_latitude_longitude_from_spreadsheet(date: str) -> tuple[float, float]:
    values = get_spreadsheet_data()
    y, m, d = date.split("-")
    date = f"{y}年{int(m)}月{int(d)}日"
    for row in values:
        if row[0] == date:
            return float(row[1]), float(row[2])
    raise Exception("No data found. [get_latitude_longitude_from_spreadsheet]")


def get_manual_data_for_importance_score(date: str) -> list[int]:
    values = get_spreadsheet_data()
    y, m, d = date.split("-")
    date = f"{y}年{int(m)}月{int(d)}日"
    for row in values:
        if row[0] == date:
            v1 = row[8]
            v2 = row[9]
            v3 = row[10]
            v4 = row[11]
            v5 = row[12]
            return [int(v1), int(v2), int(v3), int(v4), int(v5)]
    raise Exception("No data found. [get_manual_data_for_importance_score]")


if __name__ == "__main__":
    print(get_latitude_longitude_from_spreadsheet("2025-01-24"))
