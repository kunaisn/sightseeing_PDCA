import math
import pyproj
from functools import partial
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import transform

# 地球の半径（メートル）
R: float = 6378137


def geodesic_point_buffer(lat: float, lon: float, meters: float) -> Polygon:
    # 球面座標系の点を中心とする円を作成
    aeqd_proj = f"+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0"
    project = partial(
        pyproj.transform,
        pyproj.Proj(aeqd_proj),
        pyproj.Proj("+proj=longlat +datum=WGS84"),
    )
    point = Point(0, 0)
    circle = point.buffer(meters)
    return transform(project, circle)


def calculate_area_moved(
    lat1: float, lon1: float, lat2: float, lon2: float, buffer_meters: float
) -> Polygon:
    # 2点間の移動面積を計算
    line = LineString([(lon1, lat1), (lon2, lat2)])
    buffer_poly = line.buffer(buffer_meters / R * 180 / math.pi, cap_style="round")
    return buffer_poly


def calculate_total_area(
    coordinates: list[tuple[float, float]], buffer_meters: float
) -> tuple[float, Polygon]:
    # 軌跡の総移動面積を計算
    total_poly = Polygon()
    for i in range(len(coordinates) - 1):
        lat1, lon1 = coordinates[i]
        lat2, lon2 = coordinates[i + 1]
        line_poly = calculate_area_moved(lat1, lon1, lat2, lon2, buffer_meters)
        total_poly = total_poly.union(line_poly)
    proj = pyproj.Proj(
        proj="aea", lat_1=total_poly.bounds[1], lat_2=total_poly.bounds[3]
    )
    wgs84 = pyproj.Proj(init="epsg:4326")
    projected_poly = transform(partial(pyproj.transform, wgs84, proj), total_poly)
    return projected_poly.area, total_poly


def calculate_coverage_ratio(
    center_lat: float,
    center_lon: float,
    radius_meters: float,
    total_area_polygon: Polygon,
) -> float:
    # 観光範囲円と総移動面積の交差部分の面積の比を計算
    circle_poly = geodesic_point_buffer(center_lat, center_lon, radius_meters)
    intersection_poly = total_area_polygon.intersection(circle_poly)
    proj = pyproj.Proj(
        proj="aea",
        lat_1=intersection_poly.bounds[1],
        lat_2=intersection_poly.bounds[3],
    )
    wgs84 = pyproj.Proj(init="epsg:4326")
    intersection_area = transform(
        partial(pyproj.transform, wgs84, proj), intersection_poly
    ).area
    circle_area = transform(partial(pyproj.transform, wgs84, proj), circle_poly).area
    return intersection_area / circle_area


def main():
    # 座標のリスト
    coordinates: list[tuple[float, float]] = [
        (35.616824414534264, 139.56440592352044),
        (35.60782236062491, 139.55758682833218),
        (35.61078838173439, 139.57271376968677),
        (35.62033528410542, 139.5695660441778),
    ]

    # 総面積を計算
    total_area, total_poly = calculate_total_area(coordinates)
    print(f"総移動面積: {total_area} 平方メートル")

    # 特定の座標の半径4km内の総移動面積の占める割合を計算
    center_lat: float = 35.61732612298189
    center_lon: float = 139.56458680083134
    radius_meters: float = 1200.0

    ratio: float = calculate_coverage_ratio(
        center_lat, center_lon, radius_meters, total_poly
    )
    print(f"観光範囲円以内で総移動面積の占める割合: {ratio * 100:.2f}%")


if __name__ == "__main__":
    main()
