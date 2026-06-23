"""
长期记忆模拟实验 + 可视化图表

模拟一个开发者在 30 天内的记忆演化，生成：
  1. 强度曲线图（7 条记忆的 R 随时间变化）
  2. 分层分布热力图（每天的 L1/L2/L3 分布）
  3. 每周分层快照堆叠柱状图
"""

from __future__ import annotations

import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from membrain.engine import CSMEngine
from membrain.strength import (
    compute_layer_thresholds,
    current_strength,
)

# ── 场景定义 ────────────────────────────────────────────────────
SCENARIOS = [
    ("tech_stack", "High-frequency", "#1a9641",
     "bun install + pytest tech stack",
     [1,2,3,4,5,6,7,9,10,12,14,17,18,19,20,21,24,25,26,27,28,29]),
    ("user_pref", "Personal pref", "#377eb8",
     "Simplified Chinese, conclusion-first answers",
     [1,2,8,14,22,28]),
    ("code_review", "Spaced (review)", "#ff7f00",
     "Code review required before changes",
     [1,3,7,15,26]),
    ("env_setup", "Moderate use", "#4daf4a",
     "Python py -3.11, .env.local config",
     [1,5,11,23]),
    ("bug_note", "Low-frequency", "#984ea3",
     "SQLite WAL busy_timeout=5000",
     [3,19]),
    ("temp_task", "One-time use", "#a65628",
     "Temp login test@example.com",
     [1]),
    ("noise", "Never used", "#999999",
     "Friday standup moved to Room B",
     []),
]


def simulate_and_plot(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    db_path = output_dir / "sim_output.db"
    if db_path.exists():
        db_path.unlink()

    engine = CSMEngine(db_path)
    memory_ids: dict[str, int] = {}

    # ── Day 0: 创建所有记忆 ─────────────────────────────────
    now = datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc)
    for mem_id, mem_type, color, content, _ in SCENARIOS:
        m = engine.add_memory(content, project_id="sim", tags=f"type:{mem_type}")
        memory_ids[mem_id] = m.id or 0
        iso = now.isoformat()
        engine.store.conn.execute(
            "UPDATE memories SET created_at=?, updated_at=?, last_accessed_at=? WHERE id=?",
            (iso, iso, iso, m.id),
        )
        engine.store.conn.commit()

    # ── Track daily data for charts ─────────────────────────────
    days_list = list(range(0, 31))
    strengths_by_mem: dict[str, list[float]] = {m_id: [] for m_id, _, _, _, _ in SCENARIOS}
    layers_by_day: list[dict[str, int]] = []  # [{L1: n, L2: n, L3: n, COLD: n}]

    # Day 0 snapshot
    all_mems = engine.store.list_all()
    active = [m for m in all_mems if m.status.value == "active"]
    s0 = [current_strength(m, now=now) for m in active]
    for mem_id, _, _, _, _ in SCENARIOS:
        strengths_by_mem[mem_id].append(0.6)  # all start at 0.6
    layers_by_day.append({"L1": 0, "L2": 0, "L3": 7, "COLD": 0})

    # ── Day 1-30: 模拟 ─────────────────────────────────────────
    for day in range(1, 31):
        now += timedelta(days=1)

        for mem_id, mem_type, color, content, access_days in SCENARIOS:
            if day in access_days:
                mid = memory_ids[mem_id]
                results = engine.search(content[:30], project_id="sim", limit=5)
                for r in results:
                    if r.memory.id == mid:
                        engine.reinforce_used(mid)
                        iso = now.isoformat()
                        engine.store.conn.execute(
                            "UPDATE memories SET last_accessed_at=? WHERE id=?", (iso, mid)
                        )
                        engine.store.conn.commit()
                        break

        # Record daily strengths
        all_mems = engine.store.list_all()
        for mem_id, _, _, _, _ in SCENARIOS:
            mid = memory_ids[mem_id]
            mem = next((m for m in all_mems if m.id == mid), None)
            if mem:
                R = current_strength(mem, now=now)
            else:
                R = 0.0
            strengths_by_mem[mem_id].append(R)

        # Record layer distribution
        active = [m for m in all_mems if m.status.value == "active"]
        strengths = [current_strength(m, now=now) for m in active]
        thresholds = compute_layer_thresholds(strengths)
        lc = {"L1": 0, "L2": 0, "L3": 0, "COLD": 0}
        for s in strengths:
            if s >= thresholds["L1"]: lc["L1"] += 1
            elif s >= thresholds["L2"]: lc["L2"] += 1
            elif s >= thresholds["L3"]: lc["L3"] += 1
            else: lc["COLD"] += 1
        layers_by_day.append(lc)

    engine.close()
    db_path.unlink()

    # ════════════════════════════════════════════════════════════
    # Chart 1: Strength curves
    # ════════════════════════════════════════════════════════════
    fig, ax = plt.subplots(figsize=(12, 5))
    for mem_id, mem_type, color, _, _ in SCENARIOS:
        ax.plot(days_list, strengths_by_mem[mem_id],
                color=color, linewidth=2, label=f"{mem_type} ({mem_id})", alpha=0.9)

    # Layer background bands
    ax.axhspan(0.85, 1.0, alpha=0.06, color="#1a9641")
    ax.axhspan(0.5, 0.85, alpha=0.04, color="#ff7f00")
    ax.axhspan(0.0, 0.5, alpha=0.04, color="#999999")
    ax.text(29.3, 0.92, "L1", fontsize=10, color="#1a9641", ha="right")
    ax.text(29.3, 0.68, "L2", fontsize=10, color="#ff7f00", ha="right")
    ax.text(29.3, 0.25, "L3", fontsize=10, color="#999999", ha="right")

    ax.set_xlabel("Day", fontsize=12)
    ax.set_ylabel("Memory Strength R", fontsize=12)
    ax.set_title("30-Day Memory Strength Evolution", fontsize=14, fontweight="bold")
    ax.set_xlim(0, 30)
    ax.set_ylim(0, 1.05)
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_locator(mticker.MultipleLocator(5))
    fig.tight_layout()
    fig.savefig(output_dir / "strength_curves.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    # ════════════════════════════════════════════════════════════
    # Chart 2: Strength heatmap (memory × day)
    # ════════════════════════════════════════════════════════════
    mem_labels = [f"{m_id}\n({m_type})" for m_id, m_type, _, _, _ in SCENARIOS]
    heatmap_data = np.array([strengths_by_mem[m_id] for m_id, _, _, _, _ in SCENARIOS])

    fig, ax = plt.subplots(figsize=(14, 5))
    im = ax.imshow(heatmap_data, aspect="auto", cmap="RdYlGn", vmin=0.0, vmax=1.0,
                   extent=[0, 30, len(mem_labels) - 0.5, -0.5])

    ax.set_yticks(range(len(mem_labels)))
    ax.set_yticklabels(mem_labels, fontsize=9)
    ax.set_xlabel("Day", fontsize=12)
    ax.set_title("Memory Strength Heatmap (Red = Low, Green = High)", fontsize=13, fontweight="bold")

    # Annotate cells with values at key days (0, 7, 14, 21, 30)
    for i in range(len(mem_labels)):
        for day in [0, 7, 14, 21, 30]:
            val = heatmap_data[i, day]
            color = "white" if val < 0.5 else "black"
            ax.text(day, i, f"{val:.2f}", ha="center", va="center",
                    fontsize=6.5, color=color, fontweight="bold")

    cbar = fig.colorbar(im, ax=ax, shrink=0.85)
    cbar.set_label("Strength R", fontsize=11)
    ax.xaxis.set_major_locator(mticker.MultipleLocator(5))
    fig.tight_layout()
    fig.savefig(output_dir / "strength_heatmap.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    # ════════════════════════════════════════════════════════════
    # Chart 3: Layer distribution stacked bar (weekly snapshots)
    # ════════════════════════════════════════════════════════════
    weeks = ["Day 0", "Day 7", "Day 14", "Day 21", "Day 28", "Day 30"]
    week_indices = [0, 7, 14, 21, 28, 30]

    l1_vals = [layers_by_day[i]["L1"] for i in week_indices]
    l2_vals = [layers_by_day[i]["L2"] for i in week_indices]
    l3_vals = [layers_by_day[i]["L3"] for i in week_indices]
    cold_vals = [layers_by_day[i]["COLD"] for i in week_indices]

    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(weeks))
    w = 0.55

    ax.bar(x, l1_vals, w, label="L1 (Top 20%)", color="#1a9641", edgecolor="white", linewidth=0.5)
    ax.bar(x, l2_vals, w, bottom=l1_vals, label="L2 (20-60%)", color="#ff7f00", edgecolor="white", linewidth=0.5)
    ax.bar(x, l3_vals, w, bottom=np.array(l1_vals) + np.array(l2_vals),
           label="L3 (60-90%)", color="#999999", edgecolor="white", linewidth=0.5)
    cold_bottom = np.array(l1_vals) + np.array(l2_vals) + np.array(l3_vals)
    ax.bar(x, cold_vals, w, bottom=cold_bottom,
           label="COLD", color="#d7191c", edgecolor="white", linewidth=0.5)

    ax.set_xticks(x)
    ax.set_xticklabels(weeks, fontsize=10)
    ax.set_ylabel("Memory Count", fontsize=12)
    ax.set_title("Layer Distribution at Weekly Snapshots", fontsize=13, fontweight="bold")
    ax.legend(loc="upper right", fontsize=9)
    ax.set_ylim(0, 8)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(1))
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "layer_distribution.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    # ── Print summary ─────────────────────────────────────────
    print("Charts saved to:", output_dir)
    print("\n  strength_curves.png      — 7 curves over 30 days")
    print("  strength_heatmap.png     — color-coded strength grid")
    print("  layer_distribution.png   — weekly stacked bar chart")

    print("\nFinal state (Day 30):")
    for mem_id, mem_type, _, _, access_days in SCENARIOS:
        R = strengths_by_mem[mem_id][-1]
        access_count = len(access_days)
        if R >= 0.85:
            layer = "L1"
        elif R >= 0.5:
            layer = "L2"
        else:
            layer = "L3"
        print(f"  {mem_id:15s} [{mem_type:16s}]  R={R:.3f}  {layer}  accesses={access_count}")


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "sim_charts"
    simulate_and_plot(out)
