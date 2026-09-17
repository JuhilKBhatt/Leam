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

import time

def _fallback_animated_graph(ticker: str, hist: pd.DataFrame, save_path: str, title: str = ""):
    """Fallback standard dark-themed 16:9 animated chart (8s duration with hold)."""
    t_start = time.time()
    print(f"[GraphAnimator] [FALLBACK] Starting fallback animated graph generation for {ticker} -> {save_path}")
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
        anim_frames = 45  # 1.5 seconds to animate completely, 6.5 seconds to hold final frame

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

        print(f"[GraphAnimator] [FALLBACK] Rendering {total_frames} frames via Matplotlib Agg...")
        ani = animation.FuncAnimation(fig, update, frames=total_frames, init_func=init, blit=False)
        writer = animation.FFMpegWriter(fps=30, bitrate=3000)
        plt.tight_layout(pad=3.0)
        ani.save(save_path, writer=writer)
        plt.close(fig)

        raw_size_kb = os.path.getsize(save_path) / 1024 if os.path.exists(save_path) else 0
        print(f"[GraphAnimator] [FALLBACK] Matplotlib render complete ({raw_size_kb:.1f} KB in {time.time() - t_start:.2f}s). Now normalizing...")
        normalize_graph_video(save_path)
        extract_graph_frames(save_path)
        print(f"[GraphAnimator] [FALLBACK] Successfully finalized fallback animated graph: {save_path}")
        return True
    except Exception as e:
        print(f"[GraphAnimator] [FALLBACK] ERROR: Fallback graph animation failed: {e}")
        return False

def normalize_graph_video(video_path: str) -> bool:
    """Normalize graph MP4 to 30fps, yuv420p, faststart H.264 for Revideo/Chromium compatibility."""
    if not os.path.exists(video_path) or os.path.getsize(video_path) < 1000:
        print(f"[GraphAnimator-Norm] Video file missing or too small to normalize: {video_path}")
        return False

    raw_size_kb = os.path.getsize(video_path) / 1024
    temp_normalized = str(video_path) + ".normalized.mp4"
    t_norm_start = time.time()
    try:
        from core.engine.gpu import detect_gpu_backend
        gpu_backend = detect_gpu_backend()

        codec_args = ["-c:v", "libx264", "-preset", "ultrafast"]
        if gpu_backend == "nvenc":
            codec_args = ["-c:v", "h264_nvenc", "-preset", "p4"]
        elif gpu_backend == "vaapi":
            from core.engine.gpu import _working_vaapi_device
            dev = _working_vaapi_device or "/dev/dri/renderD128"
            codec_args = ["-init_hw_device", f"vaapi=va:{dev}", "-filter_hw_device", "va", "-c:v", "h264_vaapi"]

        cmd = [
            "ffmpeg", "-y", "-i", str(video_path),
            *codec_args,
            "-pix_fmt", "yuv420p",
            "-r", "30",
            "-g", "15",
            "-movflags", "+faststart",
            str(temp_normalized)
        ]
        print(f"[GraphAnimator-Norm] Normalizing {Path(video_path).name} on {gpu_backend.upper()} (raw: {raw_size_kb:.1f} KB)...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode == 0 and os.path.exists(temp_normalized) and os.path.getsize(temp_normalized) > 1000:
            norm_size_kb = os.path.getsize(temp_normalized) / 1024
            os.replace(temp_normalized, video_path)
            print(f"[GraphAnimator-Norm] SUCCESS: Normalized in {time.time() - t_norm_start:.2f}s -> {norm_size_kb:.1f} KB (yuv420p, 30fps, g=15, faststart)")
            return True
        else:
            print(f"[GraphAnimator-Norm] FFMpeg normalization warning (code {result.returncode}): {result.stderr.strip()[:300]}")
            if os.path.exists(temp_normalized):
                try:
                    os.remove(temp_normalized)
                except Exception:
                    pass
            return False
    except Exception as e:
        print(f"[GraphAnimator-Norm] ERROR: Normalization exception: {e}")
        if os.path.exists(temp_normalized):
            try:
                os.remove(temp_normalized)
            except Exception:
                pass
def extract_graph_frames(video_path: str) -> int:
    """Extract individual JPEG frames from normalized graph MP4 for 100% reliable frame-by-frame rendering."""
    if not os.path.exists(video_path) or os.path.getsize(video_path) < 1000:
        return 0
    frames_dir = Path(video_path).parent / f"{Path(video_path).stem}_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    try:
        cmd = [
            "ffmpeg", "-y", "-i", str(video_path),
            "-q:v", "2",
            str(frames_dir / "frame_%04d.jpg")
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if res.returncode == 0:
            frame_files = list(frames_dir.glob("frame_*.jpg"))
            count = len(frame_files)
            print(f"[GraphAnimator-Frames] Extracted {count} frames to {frames_dir.name}/ in {time.time() - t_start:.2f}s")
            return count
        else:
            print(f"[GraphAnimator-Frames] Warning: frame extraction returncode {res.returncode}: {res.stderr[:200]}")
            return 0
    except Exception as e:
        print(f"[GraphAnimator-Frames] Error extracting frames: {e}")
        return 0

def generate_animated_graph(ticker: str, save_path: str, graph_type: str = "line", period: str = "6mo", title: str = ""):
    t_start = time.time()
    print(f"[GraphAnimator] ========================================================")
    print(f"[GraphAnimator] STARTING GRAPH GENERATION: {ticker} ({graph_type}, {period})")
    print(f"[GraphAnimator] Target Destination: {save_path}")
    print(f"[GraphAnimator] ========================================================")
    try:
        print(f"[GraphAnimator] [1/4] Fetching historical market data via yfinance for '{ticker}' (period='{period}')...")
        hist = yf.Ticker(ticker).history(period=period)
        if hist.empty:
            print(f"[GraphAnimator] ERROR: No yfinance data found for {ticker}")
            return False

        hist_clean = hist.reset_index()
        hist_clean['Date'] = pd.to_datetime(hist_clean['Date']).dt.strftime('%Y-%m-%d')
        data_subset = hist_clean[['Date', 'Close', 'Volume']].tail(75)
        csv_data = data_subset.to_csv(index=False)
        latest_price = float(hist_clean['Close'].iloc[-1])
        min_p = float(hist_clean['Close'].min())
        max_p = float(hist_clean['Close'].max())
        print(f"[GraphAnimator] [1/4] Market data loaded: {len(data_subset)} data points (Latest: ${latest_price:.2f}, Range: ${min_p:.2f} - ${max_p:.2f})")

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
6. The video MUST be 8 seconds long at 30 fps (total 240 frames). The line/bar drawing animation MUST finish quickly within 1.5 to 2.0 seconds (first 45 to 60 frames) so viewers see the full complete chart without stopping midway. For all remaining frames (frames 60 to 240), keep the complete final chart displayed continuously on screen.
   Example:
       anim_frames = 50
       idx = max(1, int((frame / anim_frames) * len(prices))) if frame < anim_frames else len(prices) - 1
7. Animation must use `matplotlib.animation.FuncAnimation(fig, update, frames=240, ...)` and write to `{save_path}` using `writer = matplotlib.animation.FFMpegWriter(fps=30, bitrate=3000)`.
8. DO NOT call `plt.show()`. Ensure `plt.close(fig)` is called after saving.
9. Add 15% top padding to max y-value so title and highest price are never cut off.
10. Use integer indexing (e.g. prices[idx]) and avoid calling .iloc on numpy arrays. Use numeric x-values (e.g. np.arange(len(prices))) with ax.set_xticks() and ax.set_xticklabels() to avoid datetime type promotion errors.
11. When clearing previous fill_between in update(), NEVER access .collections (FillBetweenPolyCollection has no attribute 'collections'). Store the fill in a 1-element list `fill = [None]`, and do: `if fill[0]: fill[0].remove()` followed by `fill[0] = ax.fill_between(...)`.
12. Output ONLY the raw Python code. Do not include markdown codeblocks (no ```python or ```), just executable Python.
"""
        print(f"[GraphAnimator] [2/4] Requesting Matplotlib animation script from LLM...")
        t_llm = time.time()
        code = gpt_request(prompt).strip()
        print(f"[GraphAnimator] [2/4] LLM responded in {time.time() - t_llm:.2f}s ({len(code)} chars of Python code)")

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

        print(f"[GraphAnimator] [3/4] Executing LLM generated animation script via subprocess ({Path(script_path).name})...")
        t_exec = time.time()
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True, timeout=90)
        exec_duration = time.time() - t_exec

        # Clean up temp script
        try:
            os.remove(script_path)
        except Exception:
            pass

        if result.returncode == 0 and os.path.exists(save_path) and os.path.getsize(save_path) > 1000:
            raw_size_kb = os.path.getsize(save_path) / 1024
            print(f"[GraphAnimator] [3/4] LLM script executed successfully in {exec_duration:.2f}s (Raw MP4: {raw_size_kb:.1f} KB)")
            print(f"[GraphAnimator] [4/4] Normalizing video for Revideo compatibility...")
            normalize_graph_video(save_path)
            extract_graph_frames(save_path)
            total_duration = time.time() - t_start
            final_size_kb = os.path.getsize(save_path) / 1024 if os.path.exists(save_path) else 0
            print(f"[GraphAnimator] COMPLETE: Graph generated and normalized in {total_duration:.2f}s -> {save_path} ({final_size_kb:.1f} KB)")
            return True
        else:
            print(f"[GraphAnimator] [3/4] LLM script execution failed (code {result.returncode}) in {exec_duration:.2f}s:")
            print(f"[GraphAnimator] Error details:\n{result.stderr.strip()[:800]}")
            print(f"[GraphAnimator] [FALLBACK] Triggering fallback animated chart generator...")
            fallback_success = _fallback_animated_graph(ticker, hist_clean.tail(75), save_path, chart_title)
            print(f"[GraphAnimator] Fallback generator result for {ticker}: {fallback_success}")
            return fallback_success

    except Exception as e:
        print(f"[GraphAnimator] ERROR: Unexpected exception generating animated graph for {ticker}: {e}")
        try:
            return _fallback_animated_graph(ticker, hist.tail(75), save_path, title)
        except Exception as fe:
            print(f"[GraphAnimator] ERROR: Fallback also failed: {fe}")
            return False

if __name__ == "__main__":
    if len(sys.argv) > 2:
        generate_animated_graph(sys.argv[1], sys.argv[2])
