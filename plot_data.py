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
    for region, values in data.items():
        harmonic_means[region] = [len(values) / np.sum(1 / (np.array(values) + 1e-12))]
    save_plot_data(harmonic_means, ["調和平均"], save_name)


def main():
    data, index_labels = get_index_for_plot_data()
    save_plot_data(
        {k: v[3:] for k, v in data.items()}, index_labels[3:], "objective.png"
    )
    save_plot_data(
        {k: v[:3] for k, v in data.items()}, index_labels[:3], "subjective.png"
    )
    save_harmonic_means(data, "harmonic_means.png")


if __name__ == "__main__":
    main()
