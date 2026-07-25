"""Plotly styling shared by all charts (light theme, validated palette)."""

import plotly.graph_objects as go

# Reference dataviz palette (light mode)
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
SERIES_1 = "#2a78d6"          # categorical slot 1 (blue)
POS = "#0ca30c"               # status good  — gains
NEG = "#d03b3b"               # status critical — losses

FONT = dict(family='system-ui, -apple-system, "Segoe UI", sans-serif', color=INK_SECONDARY, size=13)


def base_layout(fig: go.Figure, height: int = 300) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=FONT,
        showlegend=False,
        hoverlabel=dict(bgcolor="#ffffff", font=dict(color=INK, size=13)),
    )
    fig.update_xaxes(gridcolor=GRID, linecolor=BASELINE, tickfont=dict(color=INK_MUTED), zeroline=False)
    fig.update_yaxes(gridcolor=GRID, linecolor=BASELINE, tickfont=dict(color=INK_MUTED), zeroline=False)
    return fig
