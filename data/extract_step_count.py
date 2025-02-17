import json
from datetime import datetime, timedelta


def convert_to_10seconds(data):
    """
    1秒単位のqtyデータを10秒単位に集約する関数。

    Args:
        data:  StepCount.jsonのデータを読み込んだ辞書。

    Returns:
        10秒単位に集約されたデータを含む辞書。
    """

    new_data = []
    current_10sec_data = {}

    for step in data["data"]["metrics"][0]["data"]:
        # dateをdatetimeオブジェクトに変換 (秒まで)
        date_obj = datetime.strptime(
            step["date"][:-6], "%Y-%m-%d %H:%M:%S"
        )  # タイムゾーン情報を削除してparse

        # 10秒単位のキーを生成 (例: "2025-01-14 06:15:20")
        ten_sec_key = date_obj.strftime("%Y-%m-%d %H:%M:") + str(
            date_obj.second // 10 * 10
        )

        if not current_10sec_data:  # 最初のデータ or 新しい10秒区間の始まり
            current_10sec_data = {
                "date": ten_sec_key + " +0900",  # 10秒単位の開始時刻
                "qty": step["qty"],
                # "source": step["source"] # 集約する場合はsourceを保持しない（必要ならコメントアウトを外す）
            }
        elif ten_sec_key == current_10sec_data["date"][:-6]:  # 同じ10秒区間内
            current_10sec_data["qty"] += step["qty"]
            # current_10sec_data["source"] = step["source"]  #最後のsourceで更新（必要ならコメント外す）
        else:  # 次の10秒区間へ
            new_data.append(current_10sec_data)
            current_10sec_data = {
                "date": ten_sec_key + " +0900",
                "qty": step["qty"],
                # "source": step["source"]  # 集約する場合はsourceを保持しない
            }

    # 最後のデータを追加
    if current_10sec_data:
        new_data.append(current_10sec_data)

    # 元のデータ構造に戻す
    data["data"]["metrics"][0]["data"] = new_data
    return data


if __name__ == "__main__":
    with open("StepCount.json", "r") as f:
        data = json.load(f)
    # "source"キーを削除
    for i, steps in enumerate(data["data"]["metrics"][0]["data"]):
        new_step = {
            "date": steps["date"],
            "qty": steps["qty"],
        }
        data["data"]["metrics"][0]["data"][i] = new_step
    # 10秒単位に変換
    converted_data = convert_to_10seconds(data)

    with open("StepCount_10sec.json", "w") as f:
        json.dump(converted_data["data"]["metrics"][0]["data"], f, indent=4)
