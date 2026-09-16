import os
import sys
from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib
# Use Agg backend for headless video/image rendering
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.dates as mdates
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MPath
from matplotlib.font_manager import FontProperties
from matplotlib.animation import FuncAnimation, FFMpegWriter

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
LEXEND_PATH = PROJECT_ROOT / "media" / "Lexend-Regular.ttf"

def get_font(size=14, weight="normal"):
    """Returns a FontProperties instance for Lexend if available, else standard sans-serif."""
    if LEXEND_PATH.exists():
        return FontProperties(fname=str(LEXEND_PATH), size=size, weight=weight)
    return FontProperties(family="sans-serif", size=size, weight=weight)

def _format_date_ticks(ax, dates, num_ticks=5, font_size=20):
    """Configures clean date ticks formatted as Month 'YY (e.g. Sep '23)."""
    if len(dates) == 0:
        return
    idx_step = max(1, len(dates) // num_ticks)
    selected_indices = list(range(0, len(dates), idx_step))
    if len(selected_indices) > 1 and (len(dates) - 1 - selected_indices[-1]) < (idx_step * 0.6):
        selected_indices[-1] = len(dates) - 1
    elif selected_indices[-1] != len(dates) - 1:
        selected_indices.append(len(dates) - 1)
        
    tick_dates = [dates[i] for i in selected_indices]
    tick_labels = [d.strftime("%b '%y") for d in tick_dates]
    
    ax.set_xticks(selected_indices)
    ax.set_xticklabels(tick_labels, fontproperties=get_font(font_size, weight="bold"), color="#444444")
    ax.tick_params(axis='x', which='both', bottom=False, top=False, pad=14)

def render_stock_timeline_chart(
    company_name: str,
    ticker: str,
    initial_investment: float,
    prices_data: list,
    output_video_path: str,
    duration_seconds: float = 10.0,
    fps: int = 30,
    width: int = 1080,
    height: int = 1080,
    save_poster: bool = True
) -> bool:
    """
    Renders an animated stock chart video modeled after the reference image:
    - Clean white background, no spines, clean right Y-axis with '$ ' prefix
    - Lexend typography loaded from media/Lexend-Regular.ttf
    - Smooth vertical gradient fading to transparent below the line
    - Dynamic header: Company Title, Current Price ($ in green/red), Investment Value ($ ▲/▼ in green/red)
    - Fully animated with smooth easing
    """
    try:
        if not prices_data:
            print("[StockGraphTemplate] Empty prices_data provided")
            return False

        df = pd.DataFrame(prices_data)
        if 'date' not in df.columns or 'price' not in df.columns:
            print("[StockGraphTemplate] Invalid prices_data schema. Expected 'date' and 'price' keys.")
            return False

        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)

        prices = df['price'].to_numpy(dtype=float)
        dates = df['date'].tolist()
        num_points = len(prices)
        if num_points < 2:
            print("[StockGraphTemplate] Need at least 2 price points")
            return False

        first_price = prices[0]
        last_price = prices[-1]
        is_up = last_price >= first_price

        # Primary palette based on overall trajectory
        line_color = "#16a34a" if is_up else "#ef4444"
        rgb_tuple = mcolors.to_rgb(line_color)

        # Gradient colormap: from nearly transparent to soft tint
        cmap = mcolors.LinearSegmentedColormap.from_list(
            'chart_gradient',
            [(rgb_tuple[0], rgb_tuple[1], rgb_tuple[2], 0.02),
             (rgb_tuple[0], rgb_tuple[1], rgb_tuple[2], 0.38)]
        )

        min_price = float(np.min(prices))
        max_price = float(np.max(prices))
        price_range = max_price - min_price if max_price > min_price else 1.0
        y_bottom = max(0, min_price - price_range * 0.15)
        y_top = max_price + price_range * 0.15

        # Set up figure
        fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)
        fig.patch.set_facecolor('#ffffff')
        ax.set_facecolor('#ffffff')

        # Position axis inside figure allowing generous room for large header and labels
        # [left, bottom, width, height]
        ax.set_position([0.06, 0.10, 0.77, 0.61])

        ax.set_xlim(0, num_points - 1)
        ax.set_ylim(y_bottom, y_top)

        # Spines removal
        for spine in ax.spines.values():
            spine.set_visible(False)

        # Right Y-Axis with "$ " formatting
        ax.yaxis.tick_right()
        ax.yaxis.set_label_position("right")
        ax.tick_params(axis='y', which='both', right=False, left=False, labelright=True, pad=16)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: f"$ {int(v):,}"))
        for tick_label in ax.get_yticklabels():
            tick_label.set_fontproperties(get_font(20, weight="bold"))
            tick_label.set_color("#444444")

        # X-Axis configuration with large bold ticks
        _format_date_ticks(ax, dates, num_ticks=5, font_size=20)

        # Large Header Text Elements - Highly legible on mobile / YouTube Shorts
        title_font = get_font(42, weight="bold")
        label_font = get_font(26, weight="bold")
        val_font = get_font(28, weight="bold")

        title_text = fig.text(0.06, 0.93, f"{company_name}", fontproperties=title_font, color="#111111")
        lbl_curr_price = fig.text(0.06, 0.86, "Current Price: ", fontproperties=label_font, color="#333333")
        val_curr_price = fig.text(0.35, 0.86, f"$ {first_price:.2f}", fontproperties=val_font, color="#333333")

        lbl_inv_val = fig.text(0.06, 0.79, "Investment Value: ", fontproperties=label_font, color="#333333")
        val_inv_val = fig.text(0.42, 0.79, f"$ {initial_investment:.2f}", fontproperties=val_font, color="#333333")
        arrow_inv_val = fig.text(0.60, 0.79, "", fontfamily="DejaVu Sans", fontsize=30, fontweight="bold")

        # Initial layout draw to compute exact text widths
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        inv_trans = fig.transFigure.inverted()

        bbox_p = lbl_curr_price.get_window_extent(renderer=renderer)
        x_val_p = inv_trans.transform((bbox_p.x1, 0))[0] + 0.010
        val_curr_price.set_position((x_val_p, 0.86))

        bbox_inv = lbl_inv_val.get_window_extent(renderer=renderer)
        x_val_inv = inv_trans.transform((bbox_inv.x1, 0))[0] + 0.010
        val_inv_val.set_position((x_val_inv, 0.79))

        # Gradient background image container
        gradient_data = np.linspace(0, 1, 256).reshape(256, 1)
        im = ax.imshow(
            gradient_data,
            extent=[0, num_points - 1, y_bottom, y_top],
            aspect='auto',
            origin='lower',
            cmap=cmap
        )

        # Line plot with thicker line for video clarity
        line_plot, = ax.plot([], [], color=line_color, linewidth=5.0, solid_capstyle='round')
        clip_patch = None

        total_frames = max(30, int(duration_seconds * fps))

        def update_frame(frame):
            nonlocal clip_patch
            # Easing progression from 0 to 1
            progress = min(1.0, frame / (total_frames - 1))
            # Smooth cubic ease
            if progress < 0.5:
                eased = 4 * progress * progress * progress
            else:
                eased = 1 - pow(-2 * progress + 2, 3) / 2
                
            current_idx = int(eased * (num_points - 1))
            current_idx = max(1, min(current_idx, num_points - 1))

            sub_x = np.arange(current_idx + 1)
            sub_y = prices[:current_idx + 1]

            # Update line
            line_plot.set_data(sub_x, sub_y)

            # Update gradient clipping path
            if clip_patch is not None:
                clip_patch.remove()

            path_pts = [(0, y_bottom)] + list(zip(sub_x, sub_y)) + [(sub_x[-1], y_bottom), (0, y_bottom)]
            codes = [MPath.MOVETO] + [MPath.LINETO] * (len(path_pts) - 2) + [MPath.CLOSEPOLY]
            clip_path = MPath(path_pts, codes)
            clip_patch = PathPatch(clip_path, facecolor='none', edgecolor='none')
            ax.add_patch(clip_patch)
            im.set_clip_path(clip_patch)

            # Current values
            curr_p = sub_y[-1]
            shares = initial_investment / first_price
            curr_val = shares * curr_p
            curr_gain = curr_val - initial_investment

            # Price color
            p_color = "#16a34a" if curr_p >= first_price else "#ef4444"
            val_curr_price.set_text(f"$ {curr_p:.2f}")
            val_curr_price.set_color(p_color)

            # Investment Value color and Arrow
            if curr_gain >= 0:
                v_color = "#16a34a"
                arrow = "▲"
            else:
                v_color = "#ef4444"
                arrow = "▼"
                
            val_inv_val.set_text(f"$ {curr_val:,.2f}")
            val_inv_val.set_color(v_color)

            r = fig.canvas.get_renderer()
            it = fig.transFigure.inverted()
            bbox_curr_val = val_inv_val.get_window_extent(renderer=r)
            x_arrow = it.transform((bbox_curr_val.x1, 0))[0] + 0.010
            arrow_inv_val.set_position((x_arrow, 0.79))
            arrow_inv_val.set_text(arrow)
            arrow_inv_val.set_color(v_color)

            return [line_plot, im, val_curr_price, val_inv_val, arrow_inv_val]

        # First frame for static poster/preview
        update_frame(total_frames - 1)
        if save_poster:
            poster_path = str(output_video_path).rsplit('.', 1)[0] + ".png"
            fig.savefig(poster_path, dpi=100, facecolor=fig.get_facecolor(), edgecolor='none')
            print(f"[StockGraphTemplate] Saved static poster to {poster_path}")

        # Render video
        print(f"[StockGraphTemplate] Rendering {total_frames} frames to {output_video_path}...")
        anim = FuncAnimation(fig, update_frame, frames=total_frames, blit=False)
        writer = FFMpegWriter(fps=fps, codec='libx264', extra_args=['-pix_fmt', 'yuv420p', '-crf', '18'])
        anim.save(output_video_path, writer=writer)
        plt.close(fig)

        print(f"[StockGraphTemplate] Successfully rendered animated chart: {output_video_path}")
        return True

    except Exception as e:
        print(f"[StockGraphTemplate] Error rendering timeline chart: {e}")
        import traceback
        traceback.print_exc()
        plt.close('all')
        return False


def render_stock_comparison_chart(
    comp_a: dict,
    comp_b: dict,
    output_video_path: str,
    duration_seconds: float = 10.0,
    fps: int = 30,
    width: int = 1080,
    height: int = 1080,
    save_poster: bool = True
) -> bool:
    """
    Renders an animated dual-stock comparison chart video:
    - Compares Company A vs Company B normalized to investment value ($)
    - Dynamic header with current price & investment value for both stocks
    - Dual line plots with color-coded curves
    """
    try:
        prices_a = comp_a.get('prices', [])
        prices_b = comp_b.get('prices', [])
        if not prices_a or not prices_b:
            print("[StockGraphTemplate] Missing prices in comparison data")
            return False

        df_a = pd.DataFrame(prices_a)
        df_b = pd.DataFrame(prices_b)
        df_a['date'] = pd.to_datetime(df_a['date'])
        df_b['date'] = pd.to_datetime(df_b['date'])

        # Align lengths
        min_len = min(len(df_a), len(df_b))
        df_a = df_a.iloc[:min_len].reset_index(drop=True)
        df_b = df_b.iloc[:min_len].reset_index(drop=True)

        inv_a = float(comp_a.get('initial_investment', 1000.0))
        inv_b = float(comp_b.get('initial_investment', 1000.0))

        raw_a = df_a['price'].to_numpy(dtype=float)
        raw_b = df_b['price'].to_numpy(dtype=float)
        dates = df_a['date'].tolist()

        vals_a = (inv_a / raw_a[0]) * raw_a
        vals_b = (inv_b / raw_b[0]) * raw_b

        color_a = "#00b4d8"  # Cyan
        color_b = "#ff7b00"  # Vibrant Orange

        all_vals = np.concatenate([vals_a, vals_b])
        min_val = float(np.min(all_vals))
        max_val = float(np.max(all_vals))
        val_range = max_val - min_val if max_val > min_val else 1.0
        y_bottom = max(0, min_val - val_range * 0.15)
        y_top = max_val + val_range * 0.15

        fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)
        fig.patch.set_facecolor('#ffffff')
        ax.set_facecolor('#ffffff')

        ax.set_position([0.06, 0.10, 0.77, 0.61])
        ax.set_xlim(0, min_len - 1)
        ax.set_ylim(y_bottom, y_top)

        for spine in ax.spines.values():
            spine.set_visible(False)

        ax.yaxis.tick_right()
        ax.yaxis.set_label_position("right")
        ax.tick_params(axis='y', which='both', right=False, left=False, labelright=True, pad=16)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: f"$ {int(v):,}"))
        for tick_label in ax.get_yticklabels():
            tick_label.set_fontproperties(get_font(20, weight="bold"))
            tick_label.set_color("#444444")

        _format_date_ticks(ax, dates, num_ticks=5, font_size=20)

        title_font = get_font(36, weight="bold")
        lbl_font = get_font(20, weight="bold")
        num_font = get_font(22, weight="bold")

        name_a = comp_a.get('name', 'Company A')
        name_b = comp_b.get('name', 'Company B')
        ticker_a = comp_a.get('ticker', 'A')
        ticker_b = comp_b.get('ticker', 'B')

        title_str = f"{name_a} vs {name_b}"
        if len(title_str) > 28:
            title_str = f"{ticker_a} vs {ticker_b}"
        fig.text(0.06, 0.93, title_str, fontproperties=title_font, color="#111111")

        # Row A elements at y = 0.86
        txt_a_ticker = fig.text(0.06, 0.86, f"{ticker_a}", fontproperties=lbl_font, color=color_a)
        txt_a_p_lbl = fig.text(0.18, 0.86, "Price:", fontproperties=lbl_font, color="#555555")
        txt_a_p_val = fig.text(0.28, 0.86, f"$ {raw_a[0]:.2f}", fontproperties=num_font, color="#16a34a")
        txt_a_sep = fig.text(0.42, 0.86, " | Value:", fontproperties=lbl_font, color="#555555")
        txt_a_v_val = fig.text(0.55, 0.86, f"$ {inv_a:,.2f}", fontproperties=num_font, color="#16a34a")
        arrow_a_elem = fig.text(0.70, 0.86, "▲", fontfamily="DejaVu Sans", fontsize=24, fontweight="bold", color="#16a34a")

        # Row B elements at y = 0.79
        txt_b_ticker = fig.text(0.06, 0.79, f"{ticker_b}", fontproperties=lbl_font, color=color_b)
        txt_b_p_lbl = fig.text(0.18, 0.79, "Price:", fontproperties=lbl_font, color="#555555")
        txt_b_p_val = fig.text(0.28, 0.79, f"$ {raw_b[0]:.2f}", fontproperties=num_font, color="#16a34a")
        txt_b_sep = fig.text(0.42, 0.79, " | Value:", fontproperties=lbl_font, color="#555555")
        txt_b_v_val = fig.text(0.55, 0.79, f"$ {inv_b:,.2f}", fontproperties=num_font, color="#16a34a")
        arrow_b_elem = fig.text(0.70, 0.79, "▲", fontfamily="DejaVu Sans", fontsize=24, fontweight="bold", color="#16a34a")

        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        inv_trans = fig.transFigure.inverted()

        def layout_row(y_pos, ticker_elem, p_lbl, p_val, sep_elem, v_val, arrow_elem,
                       cur_p, start_p, cur_v, start_v):
            p_color = "#16a34a" if cur_p >= start_p else "#ef4444"
            v_color = "#16a34a" if cur_v >= start_v else "#ef4444"
            arrow = "▲" if cur_v >= start_v else "▼"

            p_val.set_text(f"$ {cur_p:.2f}")
            p_val.set_color(p_color)

            v_val.set_text(f"$ {cur_v:,.2f}")
            v_val.set_color(v_color)

            arrow_elem.set_text(arrow)
            arrow_elem.set_color(v_color)

            r = fig.canvas.get_renderer()
            it = fig.transFigure.inverted()

            # ticker -> p_lbl
            b0 = ticker_elem.get_window_extent(renderer=r)
            p_lbl.set_position((it.transform((b0.x1, 0))[0] + 0.010, y_pos))

            # p_lbl -> p_val
            b1 = p_lbl.get_window_extent(renderer=r)
            p_val.set_position((it.transform((b1.x1, 0))[0] + 0.006, y_pos))

            # p_val -> sep
            b2 = p_val.get_window_extent(renderer=r)
            sep_elem.set_position((it.transform((b2.x1, 0))[0] + 0.010, y_pos))

            # sep -> v_val
            b3 = sep_elem.get_window_extent(renderer=r)
            v_val.set_position((it.transform((b3.x1, 0))[0] + 0.006, y_pos))

            # v_val -> arrow
            b4 = v_val.get_window_extent(renderer=r)
            arrow_elem.set_position((it.transform((b4.x1, 0))[0] + 0.008, y_pos))

        line_a, = ax.plot([], [], color=color_a, linewidth=5.0, label=ticker_a, solid_capstyle='round')
        line_b, = ax.plot([], [], color=color_b, linewidth=5.0, label=ticker_b, solid_capstyle='round')

        total_frames = max(30, int(duration_seconds * fps))

        def update_frame(frame):
            progress = min(1.0, frame / (total_frames - 1))
            if progress < 0.5:
                eased = 4 * progress * progress * progress
            else:
                eased = 1 - pow(-2 * progress + 2, 3) / 2

            current_idx = int(eased * (min_len - 1))
            current_idx = max(1, min(current_idx, min_len - 1))

            sub_x = np.arange(current_idx + 1)
            sub_ya = vals_a[:current_idx + 1]
            sub_yb = vals_b[:current_idx + 1]

            line_a.set_data(sub_x, sub_ya)
            line_b.set_data(sub_x, sub_yb)

            cur_pa = raw_a[current_idx]
            cur_pb = raw_b[current_idx]
            cur_va = sub_ya[-1]
            cur_vb = sub_yb[-1]

            layout_row(0.86, txt_a_ticker, txt_a_p_lbl, txt_a_p_val, txt_a_sep, txt_a_v_val, arrow_a_elem,
                       cur_pa, raw_a[0], cur_va, inv_a)
            layout_row(0.79, txt_b_ticker, txt_b_p_lbl, txt_b_p_val, txt_b_sep, txt_b_v_val, arrow_b_elem,
                       cur_pb, raw_b[0], cur_vb, inv_b)

            return [line_a, line_b, txt_a_p_val, txt_a_v_val, arrow_a_elem,
                    txt_b_p_val, txt_b_v_val, arrow_b_elem]

        update_frame(total_frames - 1)
        if save_poster:
            poster_path = str(output_video_path).rsplit('.', 1)[0] + ".png"
            fig.savefig(poster_path, dpi=100, facecolor=fig.get_facecolor(), edgecolor='none')
            print(f"[StockGraphTemplate] Saved comparison poster to {poster_path}")

        print(f"[StockGraphTemplate] Rendering {total_frames} comparison frames to {output_video_path}...")
        anim = FuncAnimation(fig, update_frame, frames=total_frames, blit=False)
        writer = FFMpegWriter(fps=fps, codec='libx264', extra_args=['-pix_fmt', 'yuv420p', '-crf', '18'])
        anim.save(output_video_path, writer=writer)
        plt.close(fig)

        print(f"[StockGraphTemplate] Successfully rendered animated comparison: {output_video_path}")
        return True

    except Exception as e:
        print(f"[StockGraphTemplate] Error rendering comparison chart: {e}")
        import traceback
        traceback.print_exc()
        plt.close('all')
        return False
