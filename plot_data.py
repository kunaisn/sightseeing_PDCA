import matplotlib.pyplot as plt
import matplotlib as mpl

# 方法1: matplotlib.rc を使ってグローバルにフォントを設定 (推奨)
mpl.rc("font", family="Hiragino Sans")  # または 'Hiragino Kaku Gothic ProN' など
# mpl.rc('font', family='IPAexGothic')  # IPAexゴシックをインストールしている場合
# mpl.rc('font', family='Yu Gothic') #Windowsの例

# データ (変更なし)
data = {
    "網羅性（Coverage）": {"1": 0.172, "2": 0.178, "3": 0.108, "4": 0.129},
    "多様性（Diversity）": {"1": 0.555, "2": 0.444, "3": 0.444, "4": 0.555},
    "重要性（Importance）": {"1": 0.800, "2": 0.200, "3": 0.200, "4": 0.800},
    "一貫性（Coherence）": {"1": 0.285, "2": 0.666, "3": 0.666, "4": 1.000},
    "効率性（Efficiency）": {"1": 0.146, "2": 0.328, "3": 0.597, "4": 0.534},
}

# x軸のラベル
places = [
    ("1", "戸塚"),
    ("2", "日野"),
    ("3", "古河"),
    ("4", "向ヶ丘遊園"),
]

# プロットの準備
plt.figure(figsize=(10, 6))

# 各指標の折れ線グラフをプロット
for metric, values in data.items():
    y_values = [values[label[0]] for label in places]
    plt.plot([l[1] for l in places], y_values, marker="o", label=metric)

# グラフの装飾 (fontproperties は不要)
plt.xlabel("データセット")  # x軸ラベル
plt.ylabel("値")  # y軸ラベル
plt.title("各指標の比較")  # タイトル
plt.legend()  # 凡例
plt.grid(True)  # グリッド線
plt.ylim(0, 1.1)  # y軸の範囲
plt.xticks(rotation=45)  # x軸ラベルを45度回転

# グラフを表示
plt.show()


# 方法2:  個別に fontproperties を指定 (非推奨 - グローバル設定の方が楽)
# import matplotlib.font_manager as fm

# font_path = "/System/Library/Fonts/Supplemental/Hiragino Sans W3.ttc"  # 例: ヒラギノ角ゴシック W3
# # font_path = "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"  # 上記が動作しない場合、日本語のファイル名で試す
# # font_path = "/Library/Fonts/ipaexg.ttf" # IPAexゴシックの例
# font_prop = fm.FontProperties(fname=font_path)

# (以下、plt.xlabel, plt.ylabel, plt.title, plt.legend で fontproperties=font_prop を指定)
# plt.xlabel("データセット", fontproperties=font_prop)
# ... (他も同様)
