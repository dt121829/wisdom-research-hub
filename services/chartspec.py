"""Charts the assistant asks for, rendered from a declared spec.

The model does not run code. It emits a small JSON block describing the chart it
wants, and this module validates that description and draws it — so a bad or
hostile spec can only ever produce a wrong-looking chart, never execution.

Spec shape:
    {"type": "line" | "bar" | "barh" | "scatter",
     "title": "...", "x_label": "...", "y_label": "...", "unit": "%" | "$" | "",
     "labels": ["Jan", "Feb", ...],
     "series": [{"name": "S&P 500", "values": [1, 2, 3]}, ...],
     "note": "where the numbers came from"}
"""

import json
import re

import plotly.graph_objects as go

from services import charts

BLOCK_RE = re.compile(r"```chartspec\s*(.*?)```", re.S | re.I)

TYPES = {"line", "bar", "barh", "scatter"}
MAX_SERIES = 6
MAX_POINTS = 60

# Categorical palette, accessible in light and dark.
PALETTE = ["#2a78d6", "#0ca30c", "#d03b3b", "#8a5cf6", "#e08b00", "#0aa6a6"]


def extract(text: str):
    """Split a reply into (clean_text, [spec, ...])."""
    specs = []
    for raw in BLOCK_RE.findall(text or ""):
        spec = _validate(raw)
        if spec:
            specs.append(spec)
    return BLOCK_RE.sub("", text or "").strip(), specs


def _validate(raw: str):
    try:
        spec = json.loads(raw.strip())
    except json.JSONDecodeError:
        return None
    if not isinstance(spec, dict):
        return None

    kind = str(spec.get("type", "line")).lower()
    if kind not in TYPES:
        kind = "line"

    labels = spec.get("labels") or []
    if not isinstance(labels, list) or not labels:
        return None
    labels = [str(x) for x in labels[:MAX_POINTS]]

    series = []
    for item in (spec.get("series") or [])[:MAX_SERIES]:
        if not isinstance(item, dict):
            continue
        values = item.get("values")
        if not isinstance(values, list) or not values:
            continue
        numbers = []
        for v in values[:len(labels)]:
            try:
                numbers.append(float(v))
            except (TypeError, ValueError):
                numbers.append(None)
        if any(n is not None for n in numbers):
            series.append({"name": str(item.get("name") or "Series"),
                           "values": numbers})
    if not series:
        return None

    return {"type": kind, "title": str(spec.get("title") or ""),
            "x_label": str(spec.get("x_label") or ""),
            "y_label": str(spec.get("y_label") or ""),
            "unit": str(spec.get("unit") or "")[:3],
            "labels": labels, "series": series,
            "note": str(spec.get("note") or "")}


def figure(spec: dict) -> go.Figure:
    """Build a Plotly figure from a validated spec, in the app's chart style."""
    fig = go.Figure()
    kind, labels = spec["type"], spec["labels"]

    for n, item in enumerate(spec["series"]):
        colour = PALETTE[n % len(PALETTE)]
        values = item["values"]
        if kind == "bar":
            fig.add_trace(go.Bar(x=labels, y=values, name=item["name"],
                                 marker=dict(color=colour, line=dict(width=0))))
        elif kind == "barh":
            fig.add_trace(go.Bar(x=values, y=labels, orientation="h",
                                 name=item["name"],
                                 marker=dict(color=colour, line=dict(width=0))))
        elif kind == "scatter":
            fig.add_trace(go.Scatter(x=labels, y=values, mode="markers",
                                     name=item["name"],
                                     marker=dict(size=9, color=colour)))
        else:
            fig.add_trace(go.Scatter(x=labels, y=values, mode="lines+markers",
                                     name=item["name"],
                                     line=dict(color=colour, width=2),
                                     marker=dict(size=6, color=colour)))

    charts.base_layout(fig, height=340)
    if spec["title"]:
        fig.update_layout(title=dict(text=spec["title"],
                                     font=dict(size=14, color=charts.INK)),
                          margin=dict(l=8, r=8, t=42, b=8))
    if len(spec["series"]) > 1:
        fig.update_layout(showlegend=True,
                          legend=dict(orientation="h", y=1.02, x=0))
    if spec["x_label"]:
        fig.update_xaxes(title_text=spec["x_label"])
    if spec["y_label"]:
        fig.update_yaxes(title_text=spec["y_label"])
    if spec["unit"] == "%":
        (fig.update_xaxes if kind == "barh" else fig.update_yaxes)(ticksuffix="%")
    elif spec["unit"] == "$":
        (fig.update_xaxes if kind == "barh" else fig.update_yaxes)(tickprefix="$")
    return fig


CHART_INSTRUCTIONS = """
Charting: when a number series would land better as a picture — a trend over time,
a comparison across names or sectors, a before/after — you may add ONE chart by
emitting a fenced block exactly like this, after your text:

```chartspec
{"type": "bar", "title": "Sector returns, 3 months", "unit": "%",
 "labels": ["Tech", "Energy", "Financials"],
 "series": [{"name": "3M return", "values": [7.7, -2.1, 4.3]}],
 "note": "Sector ETF returns from the market data above"}
```

Rules for charts:
- Use ONLY numbers that appear in the context or the user's attachment. Never
  invent or estimate a data point to make a chart look complete.
- "type" is one of line, bar, barh, scatter. Keep to one chart per reply.
- Put the source of the numbers in "note".
- If you do not have real numbers, do not emit a chart — say so in words instead.
"""
