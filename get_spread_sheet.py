import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from models.SpreadsheetManualData import SpreadsheetManualData

from dotenv import load_dotenv

load_dotenv()
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
RANGE_NAME_COORDINATE = "coordinate!A2:D"
RANGE_NAME_TRIPADVISOR = "tripadvisor!A2:K"
RANGE_NAME_INDEX = "index!A2:J"
SPREADSHEET_CREDENTIAL_PATH = os.getenv("SPREADSHEET_CREDENTIAL_PATH")
SPREADSHEET_MANUAL_DATA = None


def get_spreadsheet_manual_data() -> SpreadsheetManualData:
    global SPREADSHEET_MANUAL_DATA
    if SPREADSHEET_MANUAL_DATA is not None:
        return SPREADSHEET_MANUAL_DATA
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
    coordinate_list = [
        SpreadsheetManualData.Coordinate(
            date=row[0], name=row[1], latitude=float(row[2]), longitude=float(row[3])
        )
        for row in (
            sheet.values()
            .get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME_COORDINATE)
            .execute()["values"]
        )
    ]
    tripadvisor_list = [
        SpreadsheetManualData.TripAdvisorRank(
            date=row[0], spot=[(row[i], row[i + 5]) for i in range(1, 6)]
        )
        for row in (
            sheet.values()
            .get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME_TRIPADVISOR)
            .execute()["values"]
        )
    ]
    index_PDCA = [
        SpreadsheetManualData.IndexPDCA(
            date=row[0],
            satisfaction=row[1],
            recommendation=row[2],
            learning_rate=row[3],
            coverage=row[4],
            diversity=row[5],
            importance=row[6],
            coherence=row[7],
            efficiency=row[8],
        )
        for row in (
            sheet.values()
            .get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME_INDEX)
            .execute()["values"]
        )
    ]
    SPREADSHEET_MANUAL_DATA = SpreadsheetManualData(
        coordinate=coordinate_list,
        tripadvisor_rank=tripadvisor_list,
        index_PDCA=index_PDCA,
    )
    return SPREADSHEET_MANUAL_DATA


def transform_to_manual_date(date: str) -> str:
    y, m, d = date.split("-")
    return f"{y}年{int(m)}月{int(d)}日"


def get_latitude_longitude_from_spreadsheet(date: str) -> tuple[float, float]:
    manual_data = get_spreadsheet_manual_data()
    manual_date = transform_to_manual_date(date)
    for coordinate in manual_data.coordinate:
        if coordinate.date == manual_date:
            return coordinate.latitude, coordinate.longitude
    raise ValueError(f"Data not found for {date}")


def get_manual_data_for_importance_score(date: str) -> list[tuple[str, bool]]:
    manual_data = get_spreadsheet_manual_data()
    manual_date = transform_to_manual_date(date)
    for tripadvisor in manual_data.tripadvisor_rank:
        if tripadvisor.date == manual_date:
            return tripadvisor.spot
    raise ValueError(f"Data not found for {date}")


def get_index_for_plot_data() -> tuple[dict[str, list[float]], list[str]]:
    manual_data = get_spreadsheet_manual_data()
    # IndexPDCAの日付と一致するCoordinateのnameをラベルとする
    date_to_region = {}
    for coordinate in manual_data.coordinate:
        date_to_region[coordinate.date] = coordinate.name

    index_labels = [
        "満足度",
        "推薦度",
        "学び",
        "網羅性",
        "多様性",
        "重要性",
        "一貫性",
        "効率性",
    ]

    index_data = {}
    for index in manual_data.index_PDCA:
        label = date_to_region[index.date]
        index_data[label] = [
            index.satisfaction,
            index.recommendation,
            index.learning_rate,
            index.coverage,
            index.diversity,
            index.importance,
            index.coherence,
            index.efficiency,
        ]
    return index_data, index_labels


if __name__ == "__main__":
    print(get_latitude_longitude_from_spreadsheet("2025-01-24"))
