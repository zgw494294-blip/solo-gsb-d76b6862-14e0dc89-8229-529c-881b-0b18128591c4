"""已归档炉次工艺单导出（单文件 HTML，可脱离服务离线打开）。

- 全部内容取自归档冻结快照（见 store.get_archived_document）：不读取
  当前配方、不重新求解；同一冻结快照导出的文档内容完全一致，此后的
  配方修改、停用与服务重启均不影响文档内容（文档不含导出时刻等任何
  快照之外的数据）。
- 单文件：样式内嵌在 <style> 中，不依赖网络、外部资源或脚本。
- 名称等文本一律经 HTML 转义后按原字符展示，不会被当作标记或脚本执行。
"""

from __future__ import annotations

import html
from typing import Any

from .solver import STEP_MINUTES


def _esc(value: Any) -> str:
    """转义文本 / 属性插值：< > & " ' 全部实体化，原字符原样展示。"""
    return html.escape(str(value), quote=True)


# 内嵌样式：仅静态规则，无网络字体、无脚本、无外部资源
_CSS = """
* { box-sizing: border-box; }
body { margin: 0; padding: 24px; background: #f4f6f8; color: #1f2933;
       font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
       font-size: 14px; line-height: 1.6; }
main { max-width: 880px; margin: 0 auto; }
header.doc-head { border-bottom: 3px solid #1d6fa8; padding-bottom: 10px;
                  margin-bottom: 18px; }
h1 { font-size: 22px; margin: 0 0 6px; }
.sub { color: #52606d; font-size: 13px; margin: 0; }
section { background: #fff; border: 1px solid #dbe2ea; border-radius: 8px;
          padding: 14px 18px; margin-bottom: 16px; }
h2 { font-size: 16px; margin: 0 0 10px; color: #134e7c; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #d5dde5; padding: 6px 10px; text-align: left; }
th { background: #eef3f8; }
tbody tr:nth-child(even) { background: #f8fafc; }
dl.kv { display: flex; flex-wrap: wrap; gap: 4px 28px; margin: 0; }
dl.kv div { min-width: 240px; }
dl.kv dt { display: inline; color: #52606d; }
dl.kv dd { display: inline; margin: 0; font-weight: 600; }
p.note { color: #52606d; font-size: 13px; margin: 8px 0 0; }
footer { color: #7b8794; font-size: 12px; text-align: center; margin-top: 4px; }
@media print { body { background: #fff; padding: 0; }
                 section { break-inside: avoid; } }
"""


def render_document(doc: dict) -> str:
    """由归档冻结快照渲染单文件 HTML 工艺单（返回 str，调用方按 UTF-8 输出）。

    doc 结构见 store.get_archived_document：炉次名称 / ID / 冻结版本 /
    归档时间、按原引用顺序的配方 ID 与冻结配方版本、冻结材料参数快照，
    以及冻结的完整求解结果（首次达标区间、总时长、逐档温度）。
    """
    result = doc["result"]
    materials = list(doc["materials"])
    recipe_ids = list(doc["recipeIds"])
    versions = doc["recipeVersions"] or {}
    temperatures = list(result["temperatures"])
    step_count = int(result["stepCount"])
    total_minutes = int(result["totalMinutes"])
    name = (doc["name"] or "").strip() or "（未命名）"
    title = f"炉次 #{doc['id']} 工艺单（冻结版本 v{doc['version']}）"

    # 引用配方与冻结材料参数（按原引用顺序，与冻结快照同序）
    material_rows: list[str] = []
    for i, m in enumerate(materials):
        rid = recipe_ids[i] if i < len(recipe_ids) else "—"
        ver = versions.get(str(rid), "—")
        material_rows.append(
            "<tr>"
            f"<td>{i + 1}</td>"
            f"<td>#{_esc(rid)}</td>"
            f"<td>v{_esc(ver)}</td>"
            f"<td>{_esc(m['name'])}</td>"
            f"<td>{_esc(m['holdLow'])}</td>"
            f"<td>{_esc(m['holdHigh'])}</td>"
            f"<td>{_esc(m['duration'])}</td>"
            f"<td>{_esc(m['tolerance'])}</td>"
            "</tr>"
        )

    # 各材料首次达标区间（含起止档，档号从 1 起）
    window_rows: list[str] = []
    for w in result["windows"]:
        temps = " → ".join(str(t) for t in w["temperatures"])
        window_rows.append(
            "<tr>"
            f"<td>{_esc(w['material'])}</td>"
            f"<td>第 {_esc(w['startStep'])}～{_esc(w['endStep'])} 档</td>"
            f"<td>{_esc(w['minutes'])}</td>"
            f"<td>{_esc(temps)}</td>"
            "</tr>"
        )

    # 温度表（按档号排列；第 k 档对应 [(k-1)×5, k×5) 分钟）
    step_rows: list[str] = []
    for k, t in enumerate(temperatures, start=1):
        step_rows.append(
            f"<tr><td>{k}</td>"
            f"<td>[{(k - 1) * STEP_MINUTES}, {k * STEP_MINUTES})</td>"
            f"<td>{_esc(t)}</td></tr>"
        )

    parts = [
        "<!DOCTYPE html>",
        '<html lang="zh-CN">',
        "<head>",
        '<meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
        f"<title>{_esc(title)}</title>",
        f"<style>{_CSS}</style>",
        "</head>",
        "<body>",
        "<main>",
        '<header class="doc-head">',
        f"<h1>{_esc(title)}</h1>",
        '<p class="sub">共炉保温编排台 · 归档工艺单：单文件 HTML，全部内容取自'
        "归档冻结快照，可离线查看；此后的配方修改、停用与服务重启均不影响本单内容。</p>",
        "</header>",
        "<section>",
        "<h2>炉次信息</h2>",
        '<dl class="kv">',
        f"<div><dt>炉次名称：</dt><dd>{_esc(name)}</dd></div>",
        f"<div><dt>炉次 ID：</dt><dd>{_esc(doc['id'])}</dd></div>",
        f"<div><dt>冻结版本：</dt><dd>v{_esc(doc['version'])}</dd></div>",
        f"<div><dt>归档时间：</dt><dd>{_esc(doc['archivedAt'])}（UTC）</dd></div>",
        "</dl>",
        "</section>",
        "<section>",
        "<h2>引用配方与冻结材料参数（按原引用顺序）</h2>",
        "<table>",
        "<thead><tr>"
        "<th>顺序</th><th>配方 ID</th><th>冻结配方版本</th><th>材料名称</th>"
        "<th>保温下限 °C</th><th>保温上限 °C</th>"
        "<th>连续保温时长（分钟）</th><th>耐受上限 °C</th>"
        "</tr></thead>",
        f"<tbody>{''.join(material_rows)}</tbody>",
        "</table>",
        "</section>",
        "<section>",
        "<h2>首次达标区间与总时长</h2>",
        "<table>",
        "<thead><tr>"
        "<th>材料名称</th><th>首次达标区间（档号，含起止档）</th>"
        "<th>区间时长（分钟）</th><th>区间温度 °C</th>"
        "</tr></thead>",
        f"<tbody>{''.join(window_rows)}</tbody>",
        "</table>",
        f'<p class="note">总时长：{total_minutes} 分钟'
        f"（共 {step_count} 档，每档 {STEP_MINUTES} 分钟；"
        "档号从 1 起，第 k 档对应时间区间 [(k-1)×5, k×5) 分钟）。</p>",
        "</section>",
        "<section>",
        "<h2>温度表（按档号排列）</h2>",
        "<table>",
        "<thead><tr><th>档号</th><th>时间区间（分钟）</th><th>设定温度 °C</th></tr></thead>",
        f"<tbody>{''.join(step_rows)}</tbody>",
        "</table>",
        "</section>",
        "</main>",
        "<footer>本工艺单由共炉保温编排台自归档冻结快照导出，为只读记录。</footer>",
        "</body>",
        "</html>",
    ]
    return "\n".join(parts) + "\n"
