import json
import datetime


def extract_data_by_date(input_file, target_date):
    with open(input_file, "r") as f:
        data = json.load(f)

    extracted_data = []
    for item in data:
        try:
            # startTimeをdatetimeオブジェクトに変換
            start_time_str = item["startTime"]
            start_time_dt = datetime.datetime.strptime(
                start_time_str, "%Y-%m-%dT%H:%M:%S.%f%z"
            )

            # 日付部分を比較
            if start_time_dt.strftime("%Y-%m-%d") == target_date:
                extracted_data.append(item)
        except (KeyError, ValueError):
            print("Error: Invalid data format in one of the items.")
            continue

    output_file = f"{input_file[:-5]}_{target_date}.json"
    with open(output_file, "w") as f:
        json.dump(extracted_data, f, indent=2, ensure_ascii=False)
    print(f"Data for {target_date} extracted to '{output_file}'")


if __name__ == "__main__":
    target_date_str = "2025-02-16"
    input_json_file = f"location-history.json"
    extract_data_by_date(input_json_file, target_date_str)
