from pydantic import BaseModel


class SpreadsheetManualData(BaseModel):

    class Coordinate(BaseModel):
        date: str
        name: str
        latitude: float
        longitude: float

    coordinate: list[Coordinate]

    class TripAdvisorRank(BaseModel):
        date: str
        spot: list[tuple[str, bool]]

    tripadvisor_rank: list[TripAdvisorRank]

    class IndexPDCA(BaseModel):
        date: str
        satisfaction: float
        recommendation: float
        learning_rate: float
        coverage: float
        diversity: float
        importance: float
        coherence: float
        efficiency: float

    index_PDCA: list[IndexPDCA]
