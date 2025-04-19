import os
import pandas as pd
import re
import matplotlib.pyplot as plt
from datetime import datetime
import seaborn as sns
from io import BytesIO
import base64
sns.set(style='whitegrid')
import plotly.graph_objects as go
import plotly.express as px

def createVisualizations(path, final_visualization_path):
    with open(path, 'r', encoding='utf-8') as f:
        raw_log = f.read()

    chart1_b64 = plotAverageDuration(raw_log)
    html_timeline = plot_interactive_timeline(raw_log)
    html_graph = makeGraph(raw_log)
    makeHTML(final_visualization_path,html_timeline, html_graph, chart1_b64)


def fig_to_base64(fig):
    buf = BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return f"data:image/png;base64,{encoded}"


def plot_interactive_timeline(raw_log):

    # Extract events
    tool_events = re.findall(r"\[(.*?)\]\[🤖 TOOL USAGE STARTED: '(.*?)'\]", raw_log)
    llm_events = re.findall(r"\[🤖 LLM CALL STARTED\]: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)", raw_log)
    agent_mentions = re.findall(r"\[(.*?)\]# Agent: (.*?)$", raw_log, re.MULTILINE)

    event_log = []

    # Add tool usage events
    for ts, tool in tool_events:
        timestamp = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        event_log.append({
            "Label": tool,
            "Type": "Tool",
            "Timestamp": timestamp,
            "Details": f"Tool used: {tool} at {timestamp}"
        })

    # Add LLM call events
    for ts in llm_events:
        timestamp = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S.%f")
        event_log.append({
            "Label": "LLM",
            "Type": "LLM",
            "Timestamp": timestamp,
            "Details": f"LLM Call at {timestamp}"
        })

    # Add agent activations
    for ts, agent in agent_mentions:
        timestamp = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        event_log.append({
            "Label": agent,
            "Type": "Agent",
            "Timestamp": timestamp,
            "Details": f"Agent active: {agent} at {timestamp}"
        })

    # Create DataFrame
    df = pd.DataFrame(event_log).sort_values("Timestamp")

    if df.empty:
        print("⚠️ No events to display in the timeline.")
        return

    # Create Plotly scatter plot
    fig = px.scatter(
        df,
        x="Timestamp",
        y="Label",
        color="Label",  # unique color per label
        symbol="Type",  # shape based on event type
        title="Interactive Timeline of Crew & Task Events",
        hover_data=["Type", "Label", "Timestamp", "Details"],
        height=600,
        # width = 1500
    )

    fig.update_traces(marker=dict(size=10))
    fig.update_layout(
        yaxis_title="Agent / Tool / LLM",
        xaxis_title="Timestamp"
    )

    html_str = fig.to_html(full_html=False, include_plotlyjs='cdn')
    return html_str


def plotAverageDuration(raw_log):

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

    return chart1_b64


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
        # width=1500,
        height=2000,
        showlegend=False,
        hovermode="closest",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        margin=dict(l=20, r=20, t=40, b=20)
    )

    # fig.write_html("crew_ai_graph.html")
    html_str = fig.to_html(full_html=False, include_plotlyjs='cdn')

    return html_str

def makeHTML(final_visualization_path, html_str_timeline, html_str_graph, chart1_b64):
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Agent Log Visualizations</title>
        <style>
        body {{
            font-family: 'Roboto', sans-serif;
            margin: 0;
            padding: 2rem;
            background-color: #f4f6f9;
            color: #333;
        }}

        h1 {{
            font-size: 2.5rem;
            color: #1a202c;
            margin-bottom: 1.5rem;
            text-align: center;
        }}

        .plot {{
            background-color: #fff;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            transition: transform 0.2s ease;
        }}

        .plot:hover {{
            transform: translateY(-4px);
        }}

        h2 {{
            font-size: 1.5rem;
            color: #2d3748;
            margin-bottom: 0.5rem;
        }}

        p {{
            color: #4a5568;
            margin-bottom: 1rem;
        }}

        img {{
            max-width: 100%;
            height: auto;
            border-radius: 6px;
            border: 1px solid #e2e8f0;
        }}
    </style>
    </head>
    <body>

        <h1>Agent Log Visualizations</h1>

        <div class="plot">
            <h2>Average Duration by Event Type</h2>
            <p>This bar chart shows the average duration (in seconds) of key event types like LLM calls and tool usage.</p>
            <img src="{chart1_b64}" alt="Average Duration by Event Type">
        </div>
        
        <div class="plot">
            <h2>Crew Tasks and Events </h2>
            {html_str_timeline}
        </div>
        
        <div class="plot">
            <h2>Agent Reasoning Flow</h2>
            <p>View the interactive graph that shows the agent's reasoning process, thoughts, and tool usage:</p>
            {html_str_graph}
        </div>

    </body>
    </html>
    """

    if not os.path.exists(os.path.dirname(final_visualization_path)):
        os.makedirs(os.path.dirname(final_visualization_path), exist_ok=True)
    with open(final_visualization_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print("✅ HTML report created without saving any images to disk")
