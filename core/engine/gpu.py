"""
GPU-accelerated rendering utilities.

Auto-detects the best available hardware encoder:
  - VAAPI    (AMD / Intel on Linux)
  - NVENC    (NVIDIA on Linux)
  - VideoToolbox (Apple on macOS)
  - libx264  (CPU fallback, always works)
"""

import subprocess
import shutil
import platform

_detected_backend = None  # cached after first probe
_working_vaapi_device = None


def _probe_encoder(test_args: list[str]) -> bool:
    """Run a tiny FFmpeg encode to check if a hardware encoder works."""
    try:
        result = subprocess.run(
            test_args,
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            print(f"[GPU Probe Failed] {' '.join(test_args)}\nStderr: {result.stderr.strip()}")
        return result.returncode == 0
    except Exception as e:
        print(f"[GPU Probe Exception] {e}")
        return False


def detect_gpu_backend() -> str:
    """
    Probe FFmpeg once and return the best available backend name:
    'vaapi', 'nvenc', 'videotoolbox', or 'cpu'.
    """
    global _detected_backend, _working_vaapi_device
    if _detected_backend is not None:
        return _detected_backend

    if not shutil.which("ffmpeg"):
        _detected_backend = "cpu"
        print("[GPU] FFmpeg not found — using CPU encoding.")
        return _detected_backend

    # Use a 1080x1920 dummy to ensure the GPU can actually allocate enough memory!
    dummy_input = ["-f", "lavfi", "-i", "color=black:s=1080x1920:d=0.1"]
    tail = ["-frames:v", "1", "-f", "null", "-"]

    import glob
    render_nodes = sorted(glob.glob("/dev/dri/renderD*"))
    if not render_nodes:
        # Fallback if glob fails but device might be mapped directly
        render_nodes = ["/dev/dri/renderD128"]

    # 1. VAAPI  (AMD / Intel — Linux)
    for node in render_nodes:
        print(f"[GPU] Probing VAAPI node: {node}")
        if _probe_encoder([
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-init_hw_device", f"vaapi=va:{node}",
            "-filter_hw_device", "va",
            *dummy_input,
            "-vf", "format=nv12,hwupload",
            "-c:v", "h264_vaapi", *tail
        ]):
            _detected_backend = "vaapi"
            _working_vaapi_device = node
            print(f"[GPU] ✅ VAAPI (AMD/Intel) hardware encoding detected on {node}.")
            return _detected_backend

    # 2. NVENC  (NVIDIA — Linux / Windows)
    if _probe_encoder([
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        *dummy_input,
        "-c:v", "h264_nvenc", *tail
    ]):
        _detected_backend = "nvenc"
        print("[GPU] ✅ NVENC (NVIDIA) hardware encoding detected.")
        return _detected_backend

    # 3. VideoToolbox  (Apple — macOS)
    if platform.system() == "Darwin" and _probe_encoder([
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        *dummy_input,
        "-c:v", "h264_videotoolbox", *tail
    ]):
        _detected_backend = "videotoolbox"
        print("[GPU] ✅ VideoToolbox (macOS) hardware encoding detected.")
        return _detected_backend

    _detected_backend = "cpu"
    print("[GPU] No hardware encoder found — using CPU (libx264).")
    return _detected_backend


