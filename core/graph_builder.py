import math
import matplotlib
matplotlib.use("Agg")  # Use non-interactive backend for thread-safe canvas rendering
import matplotlib.pyplot as plt
from typing import Dict, Any, List, Tuple


def generate_investigation_graph(
    target_name: str,
    target_type: str = "Domain",
    ips: List[str] = None,
    subdomains: List[str] = None,
    mx_records: List[str] = None,
    nameservers: List[str] = None,
    techs: List[str] = None,
    social_profiles: List[str] = None,
) -> plt.Figure:
    """
    Generate an OSINT entity-relationship graph figure matching the Cyber Dark theme.
    """
    fig = plt.Figure(figsize=(9, 6), dpi=100, facecolor="#161b22")
    ax = fig.add_subplot(111)
    ax.set_facecolor("#0d1117")

    nodes = []  # (name, x, y, color, size, label)
    edges = []  # ((x1, y1), (x2, y2))

    # Center root node
    root_x, root_y = 0.0, 0.0
    nodes.append((target_name, root_x, root_y, "#58a6ff", 1400, f"TARGET\n[{target_name}]"))

    # Helper to distribute nodes in radial orbits
    categories = [
        ("IPs", ips or [], "#f0883e", 1.8),
        ("Subdomains", (subdomains or [])[:8], "#3fb950", 3.0),
        ("Mail Servers", (mx_records or [])[:4], "#a371f7", 2.2),
        ("Nameservers", (nameservers or [])[:3], "#79c0ff", 2.5),
        ("Technologies", (techs or [])[:6], "#d29922", 1.5),
        ("Social Profiles", (social_profiles or [])[:8], "#f778ba", 2.8),
    ]

    # Collect all items
    total_elements = sum(len(items) for _, items, _, _ in categories)
    if total_elements == 0:
        # Add a placeholder leaf node
        nodes.append(("No Entities", 1.5, 0.0, "#8b949e", 600, "Awaiting Data"))
        edges.append(((root_x, root_y), (1.5, 0.0)))
    else:
        current_angle = 0.0
        angle_step = (2 * math.pi) / max(total_elements, 1)

        for cat_name, items, color, radius in categories:
            for item in items:
                # Truncate text for node label
                label_text = item if len(item) <= 18 else item[:15] + ".."
                nx = radius * math.cos(current_angle)
                ny = radius * math.sin(current_angle)
                
                nodes.append((item, nx, ny, color, 650, label_text))
                edges.append(((root_x, root_y), (nx, ny)))
                current_angle += angle_step

    # Draw edges
    for (x1, y1), (x2, y2) in edges:
        ax.plot([x1, x2], [y1, y2], color="#30363d", linewidth=1.2, zorder=1, linestyle="--", alpha=0.8)

    # Draw nodes
    for name, nx, ny, color, size, lbl in nodes:
        ax.scatter(nx, ny, s=size, color=color, zorder=2, edgecolors="#ffffff", linewidths=1.2, alpha=0.95)
        ax.text(
            nx, ny, lbl,
            color="#ffffff" if color != "#ffffff" else "#000000",
            fontsize=8,
            fontweight="bold",
            ha="center",
            va="center",
            zorder=3
        )

    ax.set_title(f"VORTEX KNOWLEDGE GRAPH // {target_name.upper()}", color="#58a6ff", fontsize=11, fontweight="bold", pad=15)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_color("#30363d")

    fig.tight_layout()
    return fig
