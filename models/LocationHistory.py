from pydantic import BaseModel


class LocationHistory(BaseModel):

    class Visit(BaseModel):

        class TopCandidate(BaseModel):
            probability: str | None = None
            semanticType: str | None = None
            placeID: str | None = None
            placeLocation: str | None = None

        hierarchyLevel: str | None = None
        topCandidate: TopCandidate | None = None
        probability: str | None = None
        isTimelessVisit: str | None = None

    class Activity(BaseModel):

        class TopCandidate(BaseModel):
            type: str | None = None
            probability: str | None = None

        probability: str | None = None
        topCandidate: TopCandidate | None = None
        start: str
        end: str
        distanceMeters: str | None = None

    endTime: str
    startTime: str
    # visitかactivityはどちらかが存在する
    visit: Visit | None = None  # 訪れた場所の情報
    activity: Activity | None = None  # 移動した情報
