"""
benchmark.py — замеряет скорость NLP-обработки и строит график.
Запуск: python benchmark.py
"""
import time
import sys
import os
sys.path.append(os.path.dirname(__file__))

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from nlp_utils import process_text, get_frequency_stats, get_concordance

# ─── Тестовые данные разного размера ────────────────────────────

BASE = """
Natural language processing (NLP) is a subfield of linguistics, computer science,
and artificial intelligence concerned with the interactions between computers and human language,
in particular how to program computers to process and analyze large amounts of natural language data.
The goal is a computer capable of understanding the contents of documents, including contextual
nuances of the language within them. Technology can accurately extract information and insights.
"""

SIZES = {
    "Tiny\n~10000 words":    BASE * 200,
    "Small\n~20000 words":  BASE * 400,
    "Medium\n~30000 words":  BASE * 600,
    "Large\n~50000 words":   BASE * 1000,
    "XLarge\n~100000 words": BASE * 2000,
}

# ─── Замер ───────────────────────────────────────────────────────

labels, t_process, t_freq, t_conc, token_counts = [], [], [], [], []

print("Benchmarking...\n")
for label, text in SIZES.items():
    print(f"  {label.replace(chr(10), ' '):<22}", end="", flush=True)

    t0 = time.perf_counter()
    tokens = process_text(text)
    tp = time.perf_counter() - t0

    t0 = time.perf_counter()
    get_frequency_stats(tokens)
    tf = time.perf_counter() - t0

    t0 = time.perf_counter()
    get_concordance(tokens, "language", window=5)
    tc = time.perf_counter() - t0

    n = len(tokens)
    print(f"{n:>6} tokens  |  process={tp:.3f}s  freq={tf:.4f}s  conc={tc:.4f}s")

    labels.append(label)
    t_process.append(tp)
    t_freq.append(tf)
    t_conc.append(tc)
    token_counts.append(n)

# ─── График ──────────────────────────────────────────────────────

fig, axes = plt.subplots(1, 3, figsize=(15, 5))
fig.patch.set_facecolor("#0f1117")
for ax in axes:
    ax.set_facecolor("#1a1d27")
    ax.tick_params(colors="#94a3b8", labelsize=9)
    ax.spines[:].set_color("#2e3250")
    ax.title.set_color("#e2e8f0")
    ax.xaxis.label.set_color("#94a3b8")
    ax.yaxis.label.set_color("#94a3b8")

x = range(len(labels))
colors = ["#5b7fff", "#34d399", "#a78bfa"]

# 1. Время по шагам (stacked bar)
ax = axes[0]
b1 = ax.bar(x, t_process, color=colors[0], label="process_text")
b2 = ax.bar(x, t_freq,    color=colors[1], label="frequency_stats", bottom=t_process)
b3 = ax.bar(x, t_conc,    color=colors[2], label="concordance",
            bottom=[a+b for a,b in zip(t_process, t_freq)])
ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8)
ax.set_title("Время обработки по шагам", fontsize=11, pad=10)
ax.set_ylabel("Секунды")
ax.legend(handles=[
    mpatches.Patch(color=colors[0], label="process_text (spaCy)"),
    mpatches.Patch(color=colors[1], label="frequency_stats"),
    mpatches.Patch(color=colors[2], label="concordance"),
], fontsize=8, facecolor="#1a1d27", labelcolor="#e2e8f0", edgecolor="#2e3250")

# 2. Время spaCy vs размер текста (line)
ax = axes[1]
ax.plot(token_counts, t_process, color=colors[0], marker="o", linewidth=2, markersize=6)
for i, (n, t) in enumerate(zip(token_counts, t_process)):
    ax.annotate(f"{t:.2f}s", (n, t), textcoords="offset points",
                xytext=(0, 8), ha="center", fontsize=8, color="#94a3b8")
ax.set_title("spaCy: время vs кол-во токенов", fontsize=11, pad=10)
ax.set_xlabel("Токены")
ax.set_ylabel("Секунды")
ax.grid(True, color="#2e3250", linestyle="--", alpha=0.5)

# 3. Пропускная способность (tokens/sec)
ax = axes[2]
tps = [n/t for n, t in zip(token_counts, t_process)]
bars = ax.bar(x, tps, color=colors[0])
for bar, val in zip(bars, tps):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(tps)*0.01,
            f"{val:,.0f}", ha="center", va="bottom", fontsize=8, color="#94a3b8")
ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8)
ax.set_title("Пропускная способность (tokens/sec)", fontsize=11, pad=10)
ax.set_ylabel("Токенов в секунду")
ax.grid(True, color="#2e3250", linestyle="--", alpha=0.5, axis="y")

plt.tight_layout(pad=2)
out = os.path.join(os.path.dirname(__file__), "benchmark_results.png")
plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"\nГрафик сохранён: {out}")
plt.show()
