"""
长期记忆模拟实验

模拟一个开发者在 30 天内的记忆演化，验证：
  - 高频实用记忆 → 稳定 L1
  - 间隔重要记忆 → FSRS 效应（遗忘后重新唤起，增益更大）
  - 一次性记忆 → 自然滑向 COLD
  - 噪音记忆 → 从未检索，归档
"""

from __future__ import annotations

import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from membrain.engine import CSMEngine
from membrain.strength import (
    compute_layer_thresholds,
    current_strength,
    DECAY_RATE,
    INITIAL_STRENGTH,
)

# ── 场景定义 ────────────────────────────────────────────────────

# 每条记忆：(id, 类型, 内容, 检索日列表)
SCENARIOS = [
    ("tech_stack", "高频实用",
     "项目依赖管理使用 bun install，测试框架用 pytest。",
     # 几乎每天都被问到
     [1,2,3,4,5,6,7, 9,10,12,14, 17,18,19,20,21, 24,25,26,27,28,29]),

    ("code_review", "间隔重要",
     "所有代码变更前必须审查，不可直接修改而不检查。",
     # 只在代码审查日被查询（间隔越来越长）
     [1, 3, 7, 15, 26]),

    ("user_pref", "个人信息",
     "回答使用简体中文，简洁直接，先给结论再给步骤。",
     # 偶尔被引用
     [1, 2, 8, 14, 22, 28]),

    ("temp_task", "一次性",
     "今天临时用 test@example.com 做登录测试，不应作为长期默认邮箱。",
     # 提过一次就不再问
     [1]),

    ("noise", "噪音",
     "周五下午的站会改到了会议室 B。",
     # 从未被检索
     []),

    ("bug_note", "低频技术",
     "SQLite WAL 模式下并发写入需要设置 busy_timeout=5000。",
     # 偶尔想起来查一下
     [3, 19]),

    ("env_setup", "中度实用",
     "本地 Python 默认用 py -3.11，环境变量在 .env.local 里。",
     # 新环境时查询
     [1, 5, 11, 23]),
]


def simulate() -> None:
    db_path = Path(__file__).resolve().parent / "sim_output.db"
    if db_path.exists():
        db_path.unlink()

    engine = CSMEngine(db_path)
    memory_ids: dict[str, int] = {}

    # ── Day 0: 创建所有记忆 ─────────────────────────────────
    now = datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc)
    print("Day 0  ─ 创建 7 条记忆（初始强度 0.6）")

    for mem_id, mem_type, content, _ in SCENARIOS:
        m = engine.add_memory(content, project_id="sim", tags=f"type:{mem_type}")
        memory_ids[mem_id] = m.id or 0
        # 将创建时间设为模拟时间的 Day 0
        iso = now.isoformat()
        engine.store.conn.execute(
            "UPDATE memories SET created_at=?, updated_at=?, last_accessed_at=? WHERE id=?",
            (iso, iso, iso, m.id)
        )
        engine.store.conn.commit()
        print(f"  + {mem_id} [{mem_type}]: {content[:50]}...")

    # ── Day 1-30: 模拟时间流逝 ─────────────────────────────
    print(f"\n{'Day':<6} {'L1':>4} {'L2':>4} {'L3':>4} {'COLD':>4}  | 事件")
    print("-" * 70)

    for day in range(1, 31):
        now += timedelta(days=1)

        # 当天被检索的记忆
        accessed_today: list[int] = []
        for mem_id, mem_type, content, access_days in SCENARIOS:
            if day in access_days:
                mid = memory_ids[mem_id]
                # 模拟检索：search + reinforce
                results = engine.search(content[:30], project_id="sim", limit=5)
                for r in results:
                    if r.memory.id == mid:
                        engine.reinforce_used(mid)
                        # 修正时间戳为模拟时间
                        iso = now.isoformat()
                        engine.store.conn.execute(
                            "UPDATE memories SET last_accessed_at=? WHERE id=?",
                            (iso, mid)
                        )
                        engine.store.conn.commit()
                        accessed_today.append(mid)
                        break

        # 每天衰减（pass of time）
        # 这里我们需要手动计算，因为引擎不自动推进时间
        # 每 7 天计算一次分层快照（不调用 sleep，避免真实时间污染模拟）
        if day % 7 == 0:
            event = f"[Snapshot day {day}]"
        else:
            event = ""

        # ── 计算当天分层 ─────────────────────────────────
        all_mems = engine.store.list_all()
        active = [m for m in all_mems if m.status.value == "active"]
        strengths = [current_strength(m, now=now) for m in active]
        thresholds = compute_layer_thresholds(strengths)

        layers = {"L1": 0, "L2": 0, "L3": 0, "COLD": 0}
        for s in strengths:
            if s >= thresholds["L1"]:
                layers["L1"] += 1
            elif s >= thresholds["L2"]:
                layers["L2"] += 1
            elif s >= thresholds["L3"]:
                layers["L3"] += 1
            else:
                layers["COLD"] += 1

        # 当天事件简述
        if accessed_today:
            event = f"查询了 {len(accessed_today)} 条记忆" + (f" {event}" if event else "")
        elif event:
            pass
        else:
            event = "无访问"

        print(f"Day {day:<3} {layers['L1']:>4} {layers['L2']:>4} {layers['L3']:>4} {layers['COLD']:>4}  | {event}")

    # ── 最终报告 ──────────────────────────────────────────
    print("\n" + "=" * 70)
    print("最终状态（Day 30）")
    print("=" * 70)

    all_mems = engine.store.list_all()
    for mem_id, mem_type, content, access_days in SCENARIOS:
        mid = memory_ids[mem_id]
        mem = next((m for m in all_mems if m.id == mid), None)
        if mem is None:
            print(f"  {mem_id} [{mem_type}]: 已归档")
            continue
        R = current_strength(mem, now=now)
        if R >= thresholds["L1"]:
            layer = "L1"
        elif R >= thresholds["L2"]:
            layer = "L2"
        elif R >= thresholds["L3"]:
            layer = "L3"
        else:
            layer = "COLD"
        print(f"  {mem_id} [{mem_type}]: R={R:.3f} {layer} "
              f"access_count={mem.access_count} decay={mem.decay_rate:.4f} "
              f"boost={mem.boost:.2f} trust={mem.trust:.2f}")

    engine.close()
    db_path.unlink()  # 清理临时数据库


if __name__ == "__main__":
    simulate()
