import json
import time
from datetime import datetime
import requests
from pydantic import ValidationError
import os
import random
from dotenv import load_dotenv
import numpy as np

load_dotenv()

# Google Maps APIキーの環境変数読み込み
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")

from models.LocationHistory import LocationHistory
from models.GooglePlaceDetail import GooglePlaceDetail

from geo_area_calculator import calculate_total_area, calculate_coverage_ratio
from get_spread_sheet import (
    get_latitude_longitude_from_spreadsheet,
    get_manual_data_for_importance_score,
)


def load_location_history_list(filepath: str) -> list[LocationHistory]:
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    location_history_list: list[LocationHistory] = []
    for row in data:
        if "activity" not in row and "visit" not in row:
            continue
        try:
            location_history = LocationHistory(**row)
            location_history_list.append(location_history)
        except ValidationError as e:
            print(f"Error: {e}")

    return location_history_list


def get_google_place_details(
    place_id: str, disable_cache: bool = False
) -> GooglePlaceDetail | None:

    get_fields_list = [
        "name",
        "id",
        "types",
        "formattedAddress",
        "rating",
        "displayName",
        "primaryType",
    ]

    if not os.path.exists("places"):
        os.makedirs("places")
    # キャッシュを無効化
    if disable_cache:
        if os.path.exists(f"places/{place_id}.json"):
            os.remove(f"places/{place_id}.json")

    # 保存されたファイルがあればそれを返す
    if os.path.exists(f"places/{place_id}.json"):
        with open(f"places/{place_id}.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return GooglePlaceDetail(**data)

    # Google Places APIを用いて情報を取得（3回繰り返す）
    if GOOGLE_MAPS_API_KEY is None or GOOGLE_MAPS_API_KEY == "":
        raise Exception("Error: GOOGLE_MAPS_API_KEY is not set")

    response = None
    retry = 0
    while retry < 3:
        response = requests.get(
            f"https://places.googleapis.com/v1/places/{place_id}",
            params={
                "key": GOOGLE_MAPS_API_KEY,
                "fields": ",".join(get_fields_list),
                "languageCode": "ja",
            },
        )
        if response.status_code == 200:
            break
        if response.status_code // 100 == 4:
            raise Exception(f"Error: {response.json()}")
        retry += 1
        time.sleep(random.randint(1000, 3000) / 1000)

    if response is None:
        return None
    if response.status_code != 200:
        return None
    # 保存する
    with open(f"places/{place_id}.json", "w", encoding="utf-8") as f:
        json.dump(response.json(), f, ensure_ascii=False, indent=4)
    data = response.json()
    return GooglePlaceDetail(**data)


def get_google_place_details_list(
    visits: list[LocationHistory], disable_cache: bool = False
) -> dict[str, GooglePlaceDetail]:

    google_places: dict[str, GooglePlaceDetail] = {}
    for v in visits:
        place_id = v.visit.topCandidate.placeID
        if place_id in google_places:
            continue
        google_place = get_google_place_details(place_id, disable_cache)
        google_places[place_id] = google_place

    return google_places


def load_predefined_genres_by_google_places_api() -> dict[str, set[str]]:
    # Google Places APIで事前定義されているタイプを全て取得する
    with open("predefined_genres.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    predefined_genres = {
        cat: set(genres["subcategories"]) for cat, genres in data.items()
    }
    return predefined_genres


def parse_datetime(datetime_str: str) -> datetime:
    return datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S.%f%z")


# LocationHistoryをvisitsとactivitiesに分けて戻す
def split_location_history(
    locate_histories: list[LocationHistory],
) -> tuple[list[LocationHistory], list[LocationHistory]]:

    visits: list[LocationHistory] = []
    activities: list[LocationHistory] = []

    for locate_history in locate_histories:
        if locate_history.visit:
            visits.append(locate_history)
        elif locate_history.activity:
            activities.append(locate_history)

    return visits, activities


# 客観的スコア
def calculate_objective_score(
    locate_histories: list[LocationHistory], places: dict[str, GooglePlaceDetail]
) -> float:

    date = locate_histories[0].startTime.split("T")[0]
    lat, lon = get_latitude_longitude_from_spreadsheet(date)

    visits, activities = split_location_history(locate_histories)

    # 観光範囲円内の総移動面積の割合 coverage score
    def _calculate_coverage_score(
        _locate_histories: list[LocationHistory],
        _visits: list[LocationHistory],
        _activities: list[LocationHistory],
    ) -> float:
        coordinates = []
        for act in _locate_histories:
            if act.activity:
                coordinates.append(
                    (
                        float(act.activity.start.split(",")[0][4:]),
                        float(act.activity.start.split(",")[1]),
                    )
                )
                coordinates.append(
                    (
                        float(act.activity.end.split(",")[0][4:]),
                        float(act.activity.end.split(",")[1]),
                    )
                )
            if act.visit:
                coordinates.append(
                    (
                        float(act.visit.topCandidate.placeLocation.split(",")[0][4:]),
                        float(act.visit.topCandidate.placeLocation.split(",")[1]),
                    )
                )
        print(coordinates)

        # 総移動面積を計算
        total_area, total_poly = calculate_total_area(coordinates, 80.0)
        print(f"総移動面積(移動周囲80メートル): {total_area} 平方メートル")

        # 特定の座標の半径1.5km内の総移動面積の占める割合を計算
        center_lat = lat
        center_lon = lon
        radius_meters = 1200

        ratio = calculate_coverage_ratio(
            center_lat, center_lon, radius_meters, total_poly
        )
        print(
            f"拠点駅を中心とした円内における、総移動面積の占める割合: {ratio}",
            end="\n\n",
        )
        return ratio

    coverage_score = _calculate_coverage_score(locate_histories, visits, activities)

    # 観光スポットのジャンル多様性スコア diversity score
    def _calculate_diversity_score(
        _visits: list[LocationHistory], _places: dict[str, GooglePlaceDetail]
    ) -> float:
        all_visited_genres = set()
        for v in _visits:
            place_id = v.visit.topCandidate.placeID
            if place_id not in _places:
                continue
            all_visited_genres.update(_places[place_id].types)
        predefined_genre_categories = load_predefined_genres_by_google_places_api()

        all_visited_categories = set()
        for genre in all_visited_genres:
            for cat, genres in predefined_genre_categories.items():
                if genre in genres:
                    all_visited_categories.add(cat)
                    break

        _genre_diversity_score = len(all_visited_categories) / len(
            predefined_genre_categories
        )
        print(all_visited_categories)
        print("訪れたジャンルカテゴリの数:", len(all_visited_categories))
        print("定義されているジャンルカテゴリの数:", len(predefined_genre_categories))
        print("観光スポットのジャンル多様性スコア:", _genre_diversity_score, end="\n\n")
        return _genre_diversity_score

    genre_diversity_score = _calculate_diversity_score(visits, places)

    # p@5重要性スコア importance score
    def _calculate_importance_score(_visits: list[LocationHistory]) -> float:
        labels = get_manual_data_for_importance_score(date)
        # p@5 を計算する
        p_at_5 = sum([1 if v[1] else 0 for v in labels]) / len(labels)
        print("p@5(トリップアドバイザーから抽出):", p_at_5, end="\n\n")
        return p_at_5

    importance_score = _calculate_importance_score(visits)

    # 一貫性スコア consistency score
    def _calculate_consistency_score(
        _visits: list[LocationHistory], _places: dict[str, GooglePlaceDetail]
    ) -> float:

        # 手動入力
        predefined_spots = [
            "ChIJBYa7A0Iz-F8R6qe7HgH2XV0",
            "ChIJodnti8vM-V8RVsLa8q-bYRs",
            "ChIJ7fRyA8jM-V8RNuY11cu1Jlo",
            "ChIJBYa7A0Iz-F8R6qe7HgH2XV0",
            "ChIJhycOJtYz-F8RO54LaTG6_p0",
            "ChIJF_AqPH4z-F8Rmtm1IKiShVQ",
            "ChIJATPRNwAz-F8RcRE30FR7L78",
            "ChIJBVmy-YMz-F8R5PID8D17Cpc",
            "ChIJQ1TRt4cz-F8RxkcdIAmz2QU",
            "ChIJsfC6oXQz-F8RdA1qXiF6jLs",
            "ChIJR-yGmXMz-F8Rf07-P4u1PUM",
            "ChIJBYa7A0Iz-F8R6qe7HgH2XV0",
            "ChIJDT75skEz-F8RFWwV4pI3cpI",
        ]
        predefined_spots = set(predefined_spots)
        actually_visited_spots = set([v.visit.topCandidate.placeID for v in _visits])
        for v in _visits:
            _id = v.visit.topCandidate.placeID
            print(v.visit.topCandidate.placeID, _places[_id].displayName["text"])

        _consistency_score = len(
            set(predefined_spots) & set(actually_visited_spots)
        ) / len(actually_visited_spots | predefined_spots)
        print(
            "訪れたスポットのうち、事前に設定されたスポットの比率:",
            _consistency_score,
            end="\n\n",
        )
        return _consistency_score

    consistency_score = _calculate_consistency_score(visits, places)

    # 移動時間比率スコア efficiency score
    # def _calculate_efficiency_score(_activities: list[LocationHistory]) -> float:
    #     total_distance_meters = sum(
    #         float(a.activity.distanceMeters) for a in _activities
    #     )
    #     not_walk_distance_meters = sum(
    #         (
    #             float(a.activity.distanceMeters)
    #             if a.activity.topCandidate.type == "cycling"
    #             else float(a.activity.distanceMeters) * 0.5
    #         )
    #         for a in _activities
    #         if a.activity.topCandidate.type not in ["walking"]
    #     )
    #     _not_walk_ratio = not_walk_distance_meters / total_distance_meters
    #     print("総移動距離:", total_distance_meters)
    #     print("徒歩以外の移動時間:", not_walk_distance_meters)
    #     print("移動時間比率スコア:", _not_walk_ratio, end="\n\n")
    #     return _not_walk_ratio

    def _calculate_efficiency_score_(_date: str) -> float:
        with open("data/StepCount_10sec.json", "r") as f:
            steps = json.load(f)
        total_qty = 0.0
        start_time_str = f"{_date} 11:00:00 +0900"
        end_time_str = f"{_date} 19:00:00 +0900"
        start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S %z")
        end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S %z")
        for item in steps:
            item_date = datetime.strptime(item["date"], "%Y-%m-%d %H:%M:%S %z")
            if start_time <= item_date <= end_time:
                total_qty += item["qty"]
        print()
        print("歩数量:", total_qty)
        max_steps = 30000
        ratio = (max_steps - total_qty) / max_steps
        print("歩数比率:", ratio)
        print()
        return ratio

    efficiency_score = _calculate_efficiency_score_(date)

    def _calculate_correlation():
        satisfaction = np.array([0.8, 0.8, 0.8, 1.0, 1.0])
        efficiency = np.array([0.202, 0.419, 0.482, 0.56, 0.539])
        correlation_coefficient = np.corrcoef(satisfaction, efficiency)[0, 1]
        print("満足度と効率性の相関係数:", correlation_coefficient)

    _calculate_correlation()

    print()
    print("網羅性: ", coverage_score)
    print("多様性: ", genre_diversity_score)
    print("重要性: ", importance_score)
    print("一貫性: ", consistency_score)
    print("効率性: ", efficiency_score)


def main():
    date = "2025-02-16"
    filepath = f"data/location-history_{date}.json"
    locate_histories = load_location_history_list(filepath)
    visits, activities = split_location_history(locate_histories)
    places = get_google_place_details_list(visits)
    calculate_objective_score(locate_histories, places)


if __name__ == "__main__":
    main()
