import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import os

from get_spread_sheet import get_index_for_plot_data

mpl.rc("font", family="Hiragino Sans")


def save_plot_data(data, labels, save_name):
    plt.figure(figsize=(10, 6))
    for i, label in enumerate(labels):
        y_values = [values[i] for values in data.values()]
        plt.plot([v for v in data.keys()], y_values, marker="o", label=label)
    plt.xlabel("データセット")
    plt.ylabel("値")
    plt.title("各指標の比較")
    plt.legend()
    plt.grid(True)
    plt.ylim(0, 1.1)
    plt.xticks(rotation=45)
    dir_name = "figure"
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    plt.savefig(dir_name + "/" + save_name)


def save_harmonic_means(data, save_name):
    harmonic_means = {}
    region_labels = [r for r in data.keys()]
    # 主観スコアの相加平均を計算
    objective_values = np.array([values[:3] for values in data.values()])
    objective_means = [sum(vs) / len(vs) for vs in objective_values]
    # 主観スコアの調和平均を計算
    subjective_values = np.array([values[3:] for values in data.values()])
    subjective_means = [len(vs) / np.sum(1 / (vs + 1e-12)) for vs in subjective_values]
    # 主観スコアと客観スコアの調和平均を計算
    for o_mean, s_mean, l in zip(objective_means, subjective_means, region_labels):
        vs = np.array([o_mean, s_mean])
        harmonic_means[l] = [len(vs) / np.sum(1 / (vs + 1e-12))]
    print(harmonic_means)
    save_plot_data(harmonic_means, ["調和平均"], save_name)


def main():
    data, index_labels = get_index_for_plot_data()
    save_plot_data(
        {k: v[:3] for k, v in data.items()}, index_labels[:3], "objective.png"
    )
    save_plot_data(
        {k: v[3:] for k, v in data.items()}, index_labels[3:], "subjective.png"
    )
    save_harmonic_means(data, "harmonic_means.png")


if __name__ == "__main__":
    main()
