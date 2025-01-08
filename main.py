import json
import time
from datetime import datetime
import math
import requests
from typing import List, Dict, Tuple
from pydantic import ValidationError
import os
import random
import configparser

config_ini = configparser.ConfigParser()
config_ini.read("config.ini", encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

# Google Maps APIキーの環境変数読み込み
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")

from models.LocationHistory import LocationHistory
from models.GooglePlace import GooglePlace

from geo_area_calculator import calculate_total_area, calculate_coverage_ratio


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
) -> GooglePlace | None:

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
            return GooglePlace(**data)

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
    return GooglePlace(**data)


def get_google_place_details_list(
    visits: list[LocationHistory], disable_cache: bool = False
) -> dict[str, GooglePlace]:

    google_places: dict[str, GooglePlace] = {}
    for v in visits:
        place_id = v.visit.topCandidate.placeID
        if place_id in google_places:
            continue
        google_place = get_google_place_details(place_id, disable_cache)
        google_places[place_id] = google_place

    return google_places


def load_predefined_genres_by_google_places_api() -> dict[str, set[str]]:
    # Google Places APIで定義されているタイプを全て取得する
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
) -> Tuple[list[LocationHistory], list[LocationHistory]]:

    visits: list[LocationHistory] = []
    activities: list[LocationHistory] = []

    for locate_history in locate_histories:
        if locate_history.visit:
            visits.append(locate_history)
        elif locate_history.activity:
            activities.append(locate_history)

    return visits, activities


# 主観的スコア
def calculate_subjective_score(locate_histories: list[LocationHistory]) -> float:
    # 総観光時間を計算
    total_duration = (
        parse_datetime(locate_histories[-1].endTime)
        - parse_datetime(locate_histories[0].startTime)
    ).total_seconds()

    visits, activities = split_location_history(locate_histories)
    # スポットの滞在時間割合
    # 滞在時間の標準偏差

    # ジャンルの多様性

    # スポット訪問数
    spot_visit_count: int = len(visits)


# 客観的スコア
def calculate_objective_score(
    locate_histories: list[LocationHistory], places: dict[str, GooglePlace]
) -> float:

    visits, activities = split_location_history(locate_histories)

    # 観光範囲円内の総移動面積の割合 coverage score
    def _calculate_coverage_score(
        _visits: list[LocationHistory], _activities: list[LocationHistory]
    ) -> float:
        coordinates = []
        for act in _activities:
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

        # 総移動面積を計算
        total_area, total_poly = calculate_total_area(coordinates)
        print(f"総移動面積(移動周囲240メートル): {total_area} 平方メートル")

        # 特定の座標の半径4km内の総移動面積の占める割合を計算
        center_lat = config_ini["general"]["center-point-lat"]
        center_lon = config_ini["general"]["center-point-lon"]
        radius_meters = 2000

        ratio = calculate_coverage_ratio(
            center_lat, center_lon, radius_meters, total_poly
        )
        print(
            f"拠点駅を中心とした円内における、総移動面積の占める割合: {ratio}",
            end="\n\n",
        )
        return ratio

    coverage_score = _calculate_coverage_score(visits, activities)

    # 観光スポットのジャンル多様性スコア diversity score
    def _calculate_diversity_score(
        _visits: list[LocationHistory], _places: dict[str, GooglePlace]
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
        print("訪れたジャンルカテゴリの数:", len(all_visited_categories))
        print("定義されているジャンルカテゴリの数:", len(predefined_genre_categories))
        print("観光スポットのジャンル多様性スコア:", _genre_diversity_score, end="\n\n")
        return _genre_diversity_score

    genre_diversity_score = _calculate_diversity_score(visits, places)

    # p@5重要性スコア importance score
    def _calculate_importance_score(_visits: list[LocationHistory]) -> float:
        # 武田神社　○
        # 甲斐善光寺　×
        # 山梨県立美術館　×
        # 甲府城址　○
        # サドヤワイナリー　×
        labels = [1, 0, 0, 1, 0]
        # p@5 を計算する
        p_at_5 = sum(labels) / 5
        print("p@5(トリップアドバイザーから抽出):", p_at_5, end="\n\n")
        return p_at_5

    importance_score = _calculate_importance_score(visits)

    # 一貫性スコア consistency score
    def _calculate_consistency_score(
        _visits: list[LocationHistory], _places: dict[str, GooglePlace]
    ) -> float:
        predefined_spots = [
            "ChIJYbZS19H5G2AR9FEDjP4DPdw",
            "ChIJy9ZTqM_5G2ARjqEpyaSBwEo",
            "ChIJz87s9M35G2ARN4qw5BWReqU",
            "ChIJWwoIlDj4G2AR_SyHLzLtqPI",
            "ChIJrzPTVXb3G2AR5_U91muZo_I",
        ]
        actually_visited_spots = [v.visit.topCandidate.placeID for v in _visits]
        # for v in _visits:
        #     id = v.visit.topCandidate.placeID
        #     print(id, _places[id].displayName["text"])

        consistency_score = len(
            set(predefined_spots) & set(actually_visited_spots)
        ) / len(actually_visited_spots)
        print(
            "訪れたスポットのうち、事前に設定されたスポットの比率:",
            consistency_score,
            end="\n\n",
        )
        return consistency_score

    consistency_score = _calculate_consistency_score(visits, places)

    # 移動時間比率スコア efficiency score
    def _calculate_efficiency_score(_activities: list[LocationHistory]) -> float:
        total_duration = (
            parse_datetime(locate_histories[-1].endTime)
            - parse_datetime(locate_histories[0].startTime)
        ).total_seconds()
        total_travel_time = sum(
            (
                parse_datetime(activity.endTime) - parse_datetime(activity.startTime)
            ).total_seconds()
            for activity in _activities
        )
        _travel_time_ratio = total_travel_time / total_duration
        print("総観光時間(秒):", total_duration)
        print("移動時間(秒):", total_travel_time)
        print("移動時間比率スコア:", _travel_time_ratio, end="\n\n")
        return _travel_time_ratio

    efficiency_score = _calculate_efficiency_score(activities)

    # スポット訪問数
    spot_visit_count = len(set(v.visit.topCandidate.placeID for v in visits))
    print("訪れたスポット数:", spot_visit_count)


def main():
    date = config_ini["general"]["date"]
    filepath = f"data/location-history_{date}.json"
    locate_histories = load_location_history_list(filepath)
    visits, activities = split_location_history(locate_histories)
    places = get_google_place_details_list(visits)
    calculate_objective_score(locate_histories, places)


if __name__ == "__main__":
    main()
