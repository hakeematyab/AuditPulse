import os
import pandas as pd
import re
import matplotlib.pyplot as plt
from datetime import datetime
import seaborn as sns

sns.set(style='whitegrid')
import plotly.graph_objects as go


def createVisualizations(path, final_visualization_path):
    with open(path, 'r', encoding='utf-8') as f:
        raw_log = f.read()

    chart1_b64, chart2_b64 = createCharts(raw_log)
    html_str = makeGraph(raw_log)
    makeHTML(final_visualization_path, html_str, chart1_b64, chart2_b64)


from io import BytesIO
import base64

def fig_to_base64(fig):
    buf = BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return f"data:image/png;base64,{encoded}"

def createCharts(raw_log):
    pattern = r"\[(.*?)\]\[(.*?)\]: (.*?)$"
    matches = re.findall(pattern, raw_log, re.MULTILINE)

    log_df = pd.DataFrame(matches, columns=['timestamp', 'event', 'event_time'])
    log_df['timestamp'] = pd.to_datetime(log_df['timestamp'])
    log_df['event_time'] = pd.to_datetime(log_df['event_time'], errors='coerce')
    log_df['event_type'] = log_df['event'].str.extract(r'(✅|🤖|📋|🚀)')
    log_df['event_desc'] = log_df['event'].str.replace(r'(✅|🤖|📋|🚀)', '', regex=True).str.strip()

    duration_df = []
    for event_prefix in ['LLM CALL', 'TOOL USAGE']:
        start_mask = log_df['event_desc'].str.startswith(f"{event_prefix} STARTED")
        end_mask = log_df['event_desc'].str.startswith(f"{event_prefix} COMPLETED") | \
                   log_df['event_desc'].str.startswith(f"{event_prefix} FINISHED")
        starts = log_df[start_mask].copy()
        ends = log_df[end_mask].copy()

        for _, start in starts.iterrows():
            later_ends = ends[ends['timestamp'] > start['timestamp']]
            if not later_ends.empty:
                end = later_ends.iloc[0]
                duration = (end['timestamp'] - start['timestamp']).total_seconds()
                duration_df.append({
                    'Type': event_prefix,
                    'Start': start['timestamp'],
                    'End': end['timestamp'],
                    'Duration (s)': duration
                })
                ends.drop(end.name, inplace=True)

    duration_df = pd.DataFrame(duration_df)

    fig1, ax1 = plt.subplots(figsize=(10, 5))
    sns.barplot(data=duration_df, x='Type', y='Duration (s)', estimator='mean', ax=ax1)
    ax1.set_title('Average Duration by Event Type')
    ax1.set_ylabel('Seconds')
    ax1.set_xlabel('Event Type')
    chart1_b64 = fig_to_base64(fig1)

    gantt_data = []
    for _, row in log_df.iterrows():
        if 'STARTED' in row['event_desc'] or 'CREW' in row['event_desc']:
            label = row['event_desc'].split(':')[0] if ':' in row['event_desc'] else row['event_desc']
            gantt_data.append({'Label': label, 'Start': row['timestamp']})

    timeline_df = pd.DataFrame(gantt_data)
    timeline_df['End'] = timeline_df['Start'].shift(-1)
    timeline_df = timeline_df.dropna()
    timeline_df['Duration'] = (timeline_df['End'] - timeline_df['Start']).dt.total_seconds()

    fig2, ax2 = plt.subplots(figsize=(40, 32))
    for i, row in timeline_df.iterrows():
        ax2.barh(i, row['Duration'], left=row['Start'].timestamp(), height=0.6)
        ax2.text(row['Start'].timestamp(), i, row['Label'], va='center', ha='left')
    ax2.set_yticks([])
    ax2.set_title('Crew & Task Timeline')
    ax2.set_xlabel('Timestamp')
    chart2_b64 = fig_to_base64(fig2)

    return chart1_b64, chart2_b64


def wrap_text(text, width=60):
    # Break long text into lines of `width` characters using <br> for HTML
    return "<br>".join([text[i:i + width] for i in range(0, len(text), width)])

def makeGraph(raw_log):

    cleaned_log = re.sub(r'\x1b\[[0-9;]*m', '', raw_log)

    # Extract timestamped log lines
    log_pattern = r"\[(.*?)\]\[(.*?)\]: (.*?)$"
    matches = re.findall(log_pattern, cleaned_log, re.MULTILINE)

    thoughts = []
    tools = []

    # 1. Extract structured TOOL events from timestamped logs
    for ts, event, detail in matches:
        event_lower = event.lower()
        if 'tool usage started' in event_lower:
            tool_name_match = re.search(r"tool usage started: ['\"]?(.*?)['\"]?$", event, re.IGNORECASE)
            tools.append(tool_name_match.group(1).strip() if tool_name_match else "Tool Used")

    # 2. Extract thoughts from lines starting with "## Thought:"
    thought_pattern = r"## Thought:\s*([\s\S]*?)(?:\n##|$)"
    raw_thoughts = re.findall(thought_pattern, cleaned_log)
    for t in raw_thoughts:
        clean_t = re.sub(r"\x1b\[[0-9;]*m", "", t).strip()
        thoughts.append(clean_t.replace("\n", " "))

    # Build graph nodes
    nodes = ["Start"]
    node_labels = ["Start"]
    node_colors = ["#b3d9ff"]
    hover_texts = ["Task Start"]
    edges = []

    last_node = "Start"

    for i in range(len(thoughts)):
        t_node = f"T{i + 1}"
        nodes.append(t_node)
        node_labels.append(f"Thought {i + 1}")
        node_colors.append("#d9f2d9")
        hover_texts.append(wrap_text(thoughts[i]))
        edges.append((last_node, t_node))
        last_node = t_node

        if i < len(tools):
            l_node = f"L{i + 1}"
            nodes.append(l_node)
            node_labels.append(f"Tool {i + 1}")
            node_colors.append("#ffe0b3")
            hover_texts.append(tools[i])
            edges.append((t_node, l_node))
            last_node = l_node

    # Map node names to positions
    node_indices = {name: idx for idx, name in enumerate(nodes)}
    x_coords, y_coords = [], []
    items_per_row, x_gap, y_gap = 6, 1.5, 1.2

    for i in range(len(nodes)):
        row = i // items_per_row
        col = i % items_per_row
        x_coords.append(col * x_gap)
        y_coords.append(-row * y_gap)

    edge_x, edge_y = [], []
    for src, tgt in edges:
        i, j = node_indices[src], node_indices[tgt]
        edge_x += [x_coords[i], x_coords[j], None]
        edge_y += [y_coords[i], y_coords[j], None]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=edge_x, y=edge_y, line=dict(width=1.5, color="gray"), mode="lines", hoverinfo="none"))
    fig.add_trace(go.Scatter(
        x=x_coords, y=y_coords,
        mode="markers+text",
        text=node_labels,
        textposition="bottom center",
        hovertext=hover_texts,
        hoverinfo="text",
        marker=dict(size=30, color=node_colors, line=dict(width=1, color="black"))
    ))
    fig.update_layout(
        title="Agent Reasoning Graph",
        width=1800,
        height=900,
        showlegend=False,
        hovermode="closest",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        margin=dict(l=20, r=20, t=40, b=20)
    )

    # fig.write_html("crew_ai_graph.html")
    html_str = fig.to_html(full_html=False, include_plotlyjs='cdn')

    return html_str

def makeHTML(final_visualization_path, html_str, chart1_b64, chart2_b64):
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Agent Log Visualizations</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                padding: 2rem;
                background-color: #f9f9f9;
            }}
            h1, h2 {{
                color: #333;
            }}
            .plot {{
                margin-bottom: 40px;
            }}
            img {{
                max-width: 100%;
                border: 1px solid #ccc;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
        </style>
    </head>
    <body>

        <h1>Agent Log Visualizations</h1>

        <div class="plot">
            <h2>⏱️ Average Duration by Event Type</h2>
            <p>This bar chart shows the average duration (in seconds) of key event types like LLM calls and tool usage.</p>
            <img src="{chart1_b64}" alt="Average Duration by Event Type">
        </div>

        <div class="plot">
            <h2>📋 Task Timeline Overview</h2>
            <p>A horizontal timeline showing when each crew or task-related event occurred, ordered by timestamp.</p>
            <img src="{chart2_b64}" alt="Crew & Task Timeline">
        </div>

        <div class="plot">
            <h2>🤖 Agent Reasoning Flow</h2>
            <p>View the interactive graph that shows the agent's reasoning process, thoughts, and tool usage:</p>
            {html_str}
        </div>

    </body>
    </html>
    """

    if not os.path.exists(os.path.dirname(final_visualization_path)):
        os.makedirs(os.path.dirname(final_visualization_path), exist_ok=True)
    with open(final_visualization_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print("✅ HTML report created without saving any images to disk")
