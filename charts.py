import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

NAVY = "#101D33"
BLUE = "#2878B5"
CYAN = "#16B8C4"
ORANGE = "#F4A62A"
PALETTE = [BLUE, CYAN, ORANGE, "#8B7CF6", "#4DAA75", "#E36C83", "#7393B3"]


def style(fig, height=360):
    light = st.session_state.get("ama_theme", "dark") == "light"
    text = "#20364D" if light else "#DCE7F4"
    grid = "rgba(50,80,110,.13)" if light else "rgba(150,175,205,.16)"
    hover_bg = "#FFFFFF" if light else NAVY
    fig.update_layout(
        height=height, margin=dict(l=14, r=14, t=54, b=18),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, Arial", color=text, size=12),
        title_font=dict(size=15, color=text),
        legend_title_text="", hoverlabel=dict(bgcolor=hover_bg, font_color=text),
        transition_duration=350,
    )
    fig.update_xaxes(showgrid=False, zeroline=False, color=text, automargin=True)
    fig.update_yaxes(gridcolor=grid, zeroline=False, color=text, automargin=True)
    return fig


def bar(data, x, y, title, color=None, orientation=None):
    fig = px.bar(data, x=x, y=y, title=title, color=color,
                 color_discrete_sequence=PALETTE, orientation=orientation,
                 text_auto=".2s")
    fig.update_traces(marker_line_width=0, opacity=.92)
    return style(fig)


def line(data, x, y, title, color=None):
    fig = px.line(data, x=x, y=y, title=title, color=color,
                  markers=True, color_discrete_sequence=PALETTE)
    fig.update_traces(line=dict(width=3), marker=dict(size=7))
    return style(fig)


def donut(data, names, values, title):
    fig = px.pie(data, names=names, values=values, hole=.64, title=title,
                 color_discrete_sequence=PALETTE)
    fig.update_traces(textposition="inside", textinfo="percent+label",
                      marker=dict(line=dict(color="rgba(0,0,0,.12)", width=1)))
    return style(fig)


def pareto(data, label, value, title):
    d = data.sort_values(value, ascending=False).copy()
    total = d[value].sum()
    d["cumul_pct"] = d[value].cumsum() / total * 100 if total else 0
    fig = go.Figure()
    fig.add_bar(x=d[label], y=d[value], name="Ordres", marker_color=BLUE)
    fig.add_scatter(x=d[label], y=d["cumul_pct"], name="Cumul (%)", yaxis="y2",
                    mode="lines+markers", line=dict(color=ORANGE, width=3))
    fig.update_layout(title=title, yaxis=dict(title="Nombre d’ordres"),
                      yaxis2=dict(title="Cumul (%)", overlaying="y", side="right", range=[0, 105]))
    return style(fig)
