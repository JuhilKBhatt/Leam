import os
import sys
import pandas as pd
import yfinance as yf
from pathlib import Path
import subprocess
import json

project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(project_root))

from core.api.llm import gpt_request

def _fallback_animated_graph(ticker: str, hist: pd.DataFrame, save_path: str, title: str = ""):
    """Fallback standard dark-themed 16:9 animated chart (8s duration with hold)."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.animation as animation
        import numpy as np

        data = hist.reset_index()
        dates = pd.to_datetime(data['Date']).dt.strftime('%b %d').tolist()
        prices = data['Close'].tolist()
        n_data = len(prices)

        # 30 fps, 8 seconds = 240 frames
        total_frames = 240
        anim_frames = 90  # 3 seconds to animate, 5 seconds to hold final frame

        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(16, 9), dpi=100)
        fig.patch.set_facecolor('#0f1117')
        ax.set_facecolor('#0f1117')

        chart_title = title or f"{ticker} Stock Performance"
        ax.set_title(chart_title, fontsize=28, fontweight='bold', color='#ffffff', pad=25)
        ax.tick_params(colors='#888888', labelsize=14)
        ax.grid(True, linestyle='--', color='#222736', alpha=0.7)

        min_p, max_p = min(prices), max(prices)
        y_padding = max((max_p - min_p) * 0.15, 1.0)
        ax.set_ylim(min_p - y_padding, max_p + y_padding)
        ax.set_xlim(0, max(n_data - 1, 1))

        # Show max 8 date ticks
        step = max(1, n_data // 8)
        tick_indices = list(range(0, n_data, step))
        if (n_data - 1) not in tick_indices:
            tick_indices.append(n_data - 1)
        ax.set_xticks(tick_indices)
        ax.set_xticklabels([dates[i] for i in tick_indices], rotation=30, ha='right')
        ax.yaxis.set_major_formatter('${x:,.2f}')

        color = '#00ff99' if prices[-1] >= prices[0] else '#ff4d4d'
        line, = ax.plot([], [], color=color, linewidth=3.5, label=f"{ticker} Close")
        fill = [None]
        price_text = ax.text(0.98, 0.92, '', transform=ax.transAxes,
                             fontsize=26, fontweight='bold', color=color, ha='right', va='top')

        def init():
            line.set_data([], [])
            return line, price_text

        def update(frame):
            # Map frame to data index
            if frame < anim_frames:
                idx = min(int((frame / anim_frames) * n_data), n_data - 1)
            else:
                idx = n_data - 1

            x = np.arange(idx + 1)
            y = prices[:idx + 1]
            line.set_data(x, y)
            price_text.set_text(f"${prices[idx]:,.2f}")

            if fill[0]:
                fill[0].remove()
            fill[0] = ax.fill_between(x, ax.get_ylim()[0], y, color=color, alpha=0.15)
            return line, price_text

        ani = animation.FuncAnimation(fig, update, frames=total_frames, init_func=init, blit=False)
        writer = animation.FFMpegWriter(fps=30, bitrate=3000)
        plt.tight_layout(pad=3.0)
        ani.save(save_path, writer=writer)
        plt.close(fig)
        print(f"[Fallback] Successfully saved animated graph (8s) to {save_path}")
        return True
    except Exception as e:
        print(f"Fallback graph animation failed: {e}")
        return False

def generate_animated_graph(ticker: str, save_path: str, graph_type: str = "line", period: str = "6mo", title: str = ""):
    print(f"Fetching market data for {ticker} (period={period}) for animated graph ({graph_type})...")
    try:
        hist = yf.Ticker(ticker).history(period=period)
        if hist.empty:
            print(f"No yfinance data found for {ticker}")
            return False

        hist_clean = hist.reset_index()
        hist_clean['Date'] = pd.to_datetime(hist_clean['Date']).dt.strftime('%Y-%m-%d')
        data_subset = hist_clean[['Date', 'Close', 'Volume']].tail(75)
        csv_data = data_subset.to_csv(index=False)

        chart_title = title or f"{ticker} Market Trend"

        prompt = f"""
Write a complete standalone Python script to generate an animated 16:9 landscape stock chart MP4 video for {ticker} using matplotlib.animation.
Chart Title: "{chart_title}"
Graph Type: "{graph_type}"
Raw CSV Data:
{csv_data}

Requirements:
1. Parse this CSV data string directly within the script (use `import io`, `pd.read_csv(io.StringIO(...))`).
2. Must use 16:9 landscape aspect ratio: `fig, ax = plt.subplots(figsize=(16, 9), dpi=100)`.
3. Modern dark aesthetic: `plt.style.use('dark_background')`, dark card background color (e.g. #0f1117), neon green (#00ff99) or cyan (#00d2ff) line/bars, subtle grid lines (#222736), formatted currency on y-axis (e.g. '${{x:,.2f}}').
4. The graph type is '{graph_type}'. (line: animate line drawing progressively with fill_between; bar: animate bars; area: animate filled region).
5. Display the current animated price clearly in the top-right corner.
6. The video MUST be 8 seconds long at 30 fps (total 240 frames). Animate the drawing over the first 90 frames (3 seconds), and keep the full completed graph displayed on screen for the remaining 150 frames (5 seconds) so viewers can read it.
7. Animation must use `matplotlib.animation.FuncAnimation(fig, update, frames=240, ...)` and write to `{save_path}` using `writer = matplotlib.animation.FFMpegWriter(fps=30, bitrate=3000)`.
8. DO NOT call `plt.show()`. Ensure `plt.close(fig)` is called after saving.
9. Add 15% top padding to max y-value so title and highest price are never cut off.
10. Use integer indexing (e.g. prices[idx]) and avoid calling .iloc on numpy arrays. Use numeric x-values (e.g. np.arange(len(prices))) with ax.set_xticks() and ax.set_xticklabels() to avoid datetime type promotion errors.
11. Output ONLY the raw Python code. Do not include markdown codeblocks (no ```python or ```), just executable Python.
"""
        print(f"Asking LLM to write animation script for {ticker}...")
        code = gpt_request(prompt).strip()

        # Clean markdown wrappers if present
        if code.startswith("```python"):
            code = code.replace("```python", "", 1)
        if code.startswith("```"):
            code = code.replace("```", "", 1)
        if code.endswith("```"):
            code = code.rsplit("```", 1)[0]

        script_path = str(Path(save_path).parent / f"temp_anim_{ticker}_{int(pd.Timestamp.now().timestamp())}.py")
        with open(script_path, 'w') as f:
            f.write(code.strip())

        print(f"Executing LLM generated animation script for {ticker}...")
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True, timeout=90)

        # Clean up temp script
        try:
            os.remove(script_path)
        except Exception:
            pass

        if result.returncode == 0 and os.path.exists(save_path) and os.path.getsize(save_path) > 1000:
            print(f"Successfully generated animated graph via LLM: {save_path}")
            return True
        else:
            print(f"LLM script execution failed (code {result.returncode}):\n{result.stderr}")
            print("Running fallback animated chart generator...")
            return _fallback_animated_graph(ticker, hist_clean.tail(75), save_path, chart_title)

    except Exception as e:
        print(f"Failed to generate animated graph for {ticker}: {e}")
        try:
            return _fallback_animated_graph(ticker, hist.tail(75), save_path, title)
        except Exception:
            return False

if __name__ == "__main__":
    if len(sys.argv) > 2:
        generate_animated_graph(sys.argv[1], sys.argv[2])
