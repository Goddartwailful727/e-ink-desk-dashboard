#!/usr/bin/env python3
"""每日09:30自动推学习计划和DDL到墨水屏看板。"""

import json
import urllib.request
from datetime import date, datetime

BASE = "http://localhost:8646"

# ── 考试日程 ──
EXAMS = [
    ("词汇小测",   date(2026, 6, 10)),
    ("行政诉讼法", date(2026, 6, 16)),
    ("国社下",     date(2026, 6, 18)),
    ("刑诉",       date(2026, 6, 21)),
    ("知产",       date(2026, 6, 22)),
    ("商法",       date(2026, 6, 24)),
    ("法职伦",     date(2026, 6, 25)),
    ("国公",       date(2026, 6, 25)),
]

# ── 各科开荒进度（6/2 状态）──
# 商法: 已补第1节网课，剩第2节 + 4-5章复习
# 刑诉: 从零
# 行政法: 从零
# 国社下: 3周没上 + 读书报告50分
# 知产: 商标法已学，剩著作权法
# 法职伦: 从零，纯背诵
# 国公: 刚学完国际法主体

# ── 分阶段学习逻辑 ──
# Phase 1 (6/2-6/9): 商法优先→刑诉开荒→行政法开荒
# Phase 2 (6/10-6/15): 行政法冲刺→刑诉推进→国社下读书报告
# Phase 3 (6/16-6/25): 各科逐门冲刺

SCHEDULE_SLOTS = [
    ("10:00", "12:00", "学习"),
    ("12:00", "13:00", "午饭"),
    ("13:00", "14:00", "午睡"),
    ("14:00", "16:00", "学习"),
    ("16:00", "17:00", "吉他练习"),
    ("17:00", "18:00", "晚餐"),
    ("18:00", "20:00", "学习"),
    ("20:00", "21:00", "吉他练习"),
    ("21:00", "22:00", "学习"),
    ("22:00", "23:00", "学习"),
    ("23:00", "00:00", "太极20min+复盘"),
]

def days_before(target: date) -> int:
    return (target - date.today()).days

def make_plan() -> tuple[list[dict], list[dict]]:
    today = date.today()
    d = days_before

    # ── 考试倒计时 ──
    exams = []
    for name, dt in EXAMS:
        left = (dt - today).days
        if left >= 0:
            exams.append({
                "name": name,
                "date": dt.strftime("%-m/%-d"),
                "days_left": left,
            })

    # ── 根据今天距各考试的天数决定学什么 ──
    study_plan: list[dict] = []
    study_slots = [s for s in SCHEDULE_SLOTS if s[2] == "学习"]

    def slot_task(slot_idx, task, subject, is_break=False):
        start, end, _ = SCHEDULE_SLOTS[slot_idx]
        return {"time": f"{start}-{end}", "task": task, "subject": subject,
                "done": False, "break": is_break}

    def break_slot(slot_idx):
        start, end, label = SCHEDULE_SLOTS[slot_idx]
        return {"time": f"{start}-{end}", "task": label, "subject": "休息",
                "done": False, "break": True}

    # ── 填空：所有时段按顺序 ──
    # 学习时段分配策略
    # 学习时段索引: 0(10-12), 1(14-16), 2(18-20), 3(21-22), 4(22-23)
    learn_idx = 0
    tasks_queue = []  # (task_name, subject, slot_count)

    # Phase logic
    voc_exam_d = d(EXAMS[0][1])  # 词汇小测
    adm_exam_d = d(EXAMS[1][1])  # 行政法
    soc_exam_d = d(EXAMS[2][1])  # 国社下
    crim_exam_d = d(EXAMS[3][1]) # 刑诉
    ip_exam_d = d(EXAMS[4][1])   # 知产
    com_exam_d = d(EXAMS[5][1])  # 商法
    eth_exam_d = d(EXAMS[6][1])  # 法职伦
    int_exam_d = d(EXAMS[7][1])  # 国公

    # ── 构建今日学习内容 ──
    if voc_exam_d <= 3:
        # 词汇小测临考（最后3天）
        tasks_queue = [
            ("词汇·冲刺背诵", "词汇", 2),
            ("词汇·真题演练", "词汇", 1),
            ("商法·复习", "商法", 1),
            ("刑诉·开荒", "刑诉", 1),
        ]
    elif adm_exam_d <= 3:
        # 行政法临考
        tasks_queue = [
            ("行政法·冲刺背诵", "行政法", 3),
            ("商法·案例练习", "商法", 1),
            ("刑诉·复习", "刑诉", 1),
        ]
    elif soc_exam_d <= 3:
        # 国社下临考
        tasks_queue = [
            ("国社下·冲刺背诵", "国社下", 2),
            ("行政法·复习", "行政法", 1),
            ("刑诉·复习", "刑诉", 1),
            ("商法·查漏补缺", "商法", 1),
        ]
    elif crim_exam_d <= 4:
        # 刑诉临考
        tasks_queue = [
            ("刑诉·冲刺背诵", "刑诉", 3),
            ("商法·查漏补缺", "商法", 1),
            ("国社下·复习", "国社下", 1),
        ]
    elif ip_exam_d <= 3:
        # 知产临考
        tasks_queue = [
            ("知产·冲刺背诵", "知产", 2),
            ("商法·查漏补缺", "商法", 1),
            ("刑诉·错题回顾", "刑诉", 1),
            ("行政法·快速回顾", "行政法", 1),
        ]
    elif com_exam_d <= 5:
        # 商法临考
        tasks_queue = [
            ("商法·案例冲刺", "商法", 3),
            ("刑诉·查漏补缺", "刑诉", 1),
            ("国公·背诵", "国公", 1),
        ]
    elif soc_exam_d <= 10:
        # 国社下读书报告周
        tasks_queue = [
            ("国社下·读书报告", "国社下", 2),
            ("商法·补网课+复习", "商法", 1),
            ("刑诉·开荒", "刑诉", 1),
            ("行政法·开荒", "行政法", 1),
        ]
    else:
        # 常规阶段：商法优先 + 刑诉开荒 + 行政法开荒
        tasks_queue = [
            ("商法·补网课/复习", "商法", 2),
            ("刑诉·开荒", "刑诉", 1),
            ("行政法·开荒", "行政法", 1),
            ("词汇·每日积累", "词汇", 1),
        ]

    # ── 铺排到时段 ──
    for slot_idx, (start, end, _) in enumerate(SCHEDULE_SLOTS):
        if SCHEDULE_SLOTS[slot_idx][2] != "学习":
            study_plan.append(break_slot(slot_idx))
        else:
            if tasks_queue:
                task_name, subject, _ = tasks_queue[0]
                remaining = tasks_queue[0][2] - 1
                study_plan.append(slot_task(slot_idx, task_name, subject))
                if remaining <= 0:
                    tasks_queue.pop(0)
                else:
                    tasks_queue[0] = (task_name, subject, remaining)
            else:
                study_plan.append(slot_task(slot_idx, "自习/复习", "综合"))

    return study_plan, exams


def push_ddl():
    today = date.today()
    items = []
    for name, dt in EXAMS:
        left = (dt - today).days
        if left >= 0:
            items.append({
                "name": name,
                "due_str": dt.isoformat(),
                "days_left": left,
                "priority": 5 if left <= 7 else (3 if left <= 14 else 1),
            })
    data = json.dumps({"items": items}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}/dashboard/ddl",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


def push_plan(items, exams):
    data = json.dumps({"items": items, "exams": exams}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}/dashboard/plan/today",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


def trigger():
    req = urllib.request.Request(
        f"{BASE}/dashboard/trigger",
        data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


if __name__ == "__main__":
    items, exams = make_plan()

    print(f"=== {date.today().isoformat()} 推送 ===")
    print(f"DDL: {len(EXAMS)} 项考试")
    print(f"计划: {len([i for i in items if not i.get('break')])} 学习项 + {len([i for i in items if i.get('break')])} 休息项")
    print(f"考试倒计时: {len(exams)} 项")

    r1 = push_ddl()
    print(f"DDL推送: ok={r1.get('ok')}, etag={r1.get('etag','')[:12]}")

    r2 = push_plan(items, exams)
    print(f"计划推送: ok={r2.get('ok')}, etag={r2.get('etag','')[:12]}")

    # 只在etag确实变化时才触发渲染
    if r1.get("etag") == r2.get("etag") and r1.get("ok") and r2.get("ok"):
        print("数据无变化，跳过渲染")
    else:
        r3 = trigger()
        print(f"渲染触发: ok={r3.get('ok')}")

    print("\n今日学习安排:")
    for i in items:
        mark = "📚" if not i.get("break") else "☕"
        done = "✓" if i.get("done") else "○"
        print(f"  {done} {i['time']} {mark} {i['task']}")

    print("\n考试倒计时:")
    for e in exams:
        print(f"  {e['name']}: {e['days_left']}天")
