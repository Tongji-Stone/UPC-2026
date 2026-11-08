"""Draw sparse grayscale figures from saved sensitivity calculations."""
from pathlib import Path
import csv
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "results/sensitivity_linear/figures"
REVIEW = ROOT / "results/chapter5_review/fig13"
MC = ROOT / "results/monte_carlo_linear"
SEED = 20261109

def draw():
    plt.rcParams.update({"font.family":"serif", "font.serif":["Times New Roman"],
        "font.size":10, "font.weight":"bold", "axes.labelweight":"bold",
        "axes.titleweight":"bold", "pdf.fonttype":42, "axes.spines.top":False,
        "axes.spines.right":False, "xtick.labelsize":9, "ytick.labelsize":9})
    rng = np.random.default_rng(SEED)
    with (REVIEW / "feasible_crossings.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    reference = json.loads((REVIEW / "summary.json").read_text(encoding="utf-8"))["baseline"]
    selected = rng.choice(len(rows), size=min(700, len(rows)), replace=False)
    vals = np.array([[float(row[k]) for k in ("y", "z", "ad")] for row in rows])
    fig, ax = plt.subplots(figsize=(6.4, 3.4), layout="constrained")
    scatter = ax.scatter(vals[selected,0], vals[selected,1], c=vals[selected,2],
        cmap="Greys", vmin=1.0, vmax=1.9, s=12, linewidths=0, alpha=.85)
    ax.scatter(reference["y"], reference["z"], marker="*", s=140, color="white",
        edgecolor="black", linewidth=1.0, zorder=5, label="Reference")
    ax.set(xlabel="Goal y (m)", ylabel="Goal z (m)")
    ax.legend(frameon=False, loc="upper right")
    bar = fig.colorbar(scatter, ax=ax, label="Drag multiplier")
    bar.ax.yaxis.label.set_fontweight("bold")
    for t in bar.ax.get_yticklabels(): t.set_fontweight("bold")
    for t in ax.get_xticklabels()+ax.get_yticklabels(): t.set_fontweight("bold")
    for ext in ("pdf", "png"): fig.savefig(FIG / ("conditional_crossings."+ext), dpi=240, bbox_inches="tight")
    plt.close(fig)
    sample = np.load(MC / "samples.npz")
    points = sample["point"][sample["event"] == 0, 1:3]
    chosen = rng.choice(len(points), size=min(1200, len(points)), replace=False)
    density, ye, ze = np.histogram2d(points[:,0], points[:,1], bins=38)
    yi = np.clip(np.searchsorted(ye, points[chosen,0], side="right") - 1, 0, density.shape[0]-1)
    zi = np.clip(np.searchsorted(ze, points[chosen,1], side="right") - 1, 0, density.shape[1]-1)
    counts = density[yi, zi]
    order = np.argsort(counts)
    summary = json.loads((MC / "summary.json").read_text(encoding="utf-8"))
    baseline = json.loads((ROOT / "results/sensitivity_linear/baseline.json").read_text(encoding="utf-8"))["event"]
    fig, ax = plt.subplots(figsize=(6.4, 3.9), layout="constrained")
    sc = ax.scatter(points[chosen[order],0], points[chosen[order],1], c=np.log1p(counts[order]),
        cmap="Greys", vmin=0, vmax=np.log1p(density.max())*1.12, s=10, linewidths=0)
    ax.scatter(baseline["y"], baseline["z"], marker="*", s=120, color="white", edgecolor="black", linewidth=1, zorder=5, label="Reference")
    ellipse = summary["ellipse_95"]
    values, vectors = np.linalg.eigh(ellipse["covariance"])
    idx = values.argsort()[::-1]; values = values[idx]; vectors = vectors[:,idx]
    angle = np.degrees(np.arctan2(vectors[1,0], vectors[0,0]))
    ax.add_patch(Ellipse(ellipse["center"], 2*np.sqrt(ellipse["empirical_d2_threshold"]*values[0]),
        2*np.sqrt(ellipse["empirical_d2_threshold"]*values[1]), angle=angle,
        fill=False, lw=1.3, color="black", label="95% sample region"))
    ax.axhline(2.33, color="black", ls="--", lw=1, label="Upper clearance")
    ax.set(xlabel="Goal y (m)", ylabel="Goal z (m)")
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    bar = fig.colorbar(sc, ax=ax); bar.set_ticks([]); bar.set_label("Density (light to dark)", fontweight="bold")
    for t in ax.get_xticklabels()+ax.get_yticklabels(): t.set_fontweight("bold")
    for ext in ("pdf", "png"): fig.savefig(FIG / ("monte_carlo_crossings."+ext), dpi=240, bbox_inches="tight")
    plt.close(fig)
    print(f"Plotted {len(selected)} of {len(rows)} constrained points and {len(chosen)} of {len(points)} Monte Carlo points; seed {SEED}.")

if __name__ == "__main__": draw()
