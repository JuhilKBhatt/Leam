"""
GPU-accelerated rendering utilities.

Auto-detects the best available hardware encoder:
  - VAAPI    (AMD / Intel on Linux)
  - NVENC    (NVIDIA on Linux)
  - VideoToolbox (Apple on macOS)
  - libx264  (CPU fallback, always works)

Provides gpu_write_videofile() as a drop-in wrapper around
MoviePy's clip.write_videofile().
"""

import subprocess
import shutil
import platform

_detected_backend = None  # cached after first probe


def _probe_encoder(test_args: list[str]) -> bool:
    """Run a tiny FFmpeg encode to check if a hardware encoder works."""
    try:
        result = subprocess.run(
            test_args,
            capture_output=True, text=True, timeout=15
        )
        return result.returncode == 0
    except Exception:
        return False


def detect_gpu_backend() -> str:
    """
    Probe FFmpeg once and return the best available backend name:
    'vaapi', 'nvenc', 'videotoolbox', or 'cpu'.
    """
    global _detected_backend
    if _detected_backend is not None:
        return _detected_backend

    if not shutil.which("ffmpeg"):
        _detected_backend = "cpu"
        print("[GPU] FFmpeg not found — using CPU encoding.")
        return _detected_backend

    dummy_input = ["-f", "lavfi", "-i", "color=black:s=64x64:d=0.1"]
    tail = ["-frames:v", "1", "-f", "null", "-"]

    # 1. VAAPI  (AMD / Intel — Linux)
    if _probe_encoder([
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-vaapi_device", "/dev/dri/renderD128",
        *dummy_input,
        "-vf", "format=nv12,hwupload",
        "-c:v", "h264_vaapi", *tail
    ]):
        _detected_backend = "vaapi"
        print("[GPU] ✅ VAAPI (AMD/Intel) hardware encoding detected.")
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


def _apply_hw_params(kwargs: dict, backend: str) -> dict:
    """
    Mutate kwargs for write_videofile to use the detected
    hardware encoder.  Returns the (possibly modified) dict.
    """
    if backend == "vaapi":
        kwargs["codec"] = "h264_vaapi"
        kwargs.pop("preset", None)          # VAAPI ignores x264 presets
        vaapi_params = [
            "-vaapi_device", "/dev/dri/renderD128",
            "-vf", "format=nv12,hwupload",
        ]
        kwargs["ffmpeg_params"] = vaapi_params + list(kwargs.get("ffmpeg_params", []))

    elif backend == "nvenc":
        kwargs["codec"] = "h264_nvenc"
        # Map x264 presets to NVENC equivalents
        preset_map = {"ultrafast": "p1", "fast": "p4", "medium": "p5"}
        old_preset = kwargs.pop("preset", "fast")
        nvenc_preset = preset_map.get(old_preset, "p4")
        kwargs["ffmpeg_params"] = [
            "-preset", nvenc_preset, "-rc", "vbr",
        ] + list(kwargs.get("ffmpeg_params", []))

    elif backend == "videotoolbox":
        kwargs["codec"] = "h264_videotoolbox"
        kwargs.pop("preset", None)          # VideoToolbox ignores x264 presets
        kwargs["ffmpeg_params"] = list(kwargs.get("ffmpeg_params", []))

    else:
        # CPU fallback — keep libx264 defaults
        if kwargs.get("codec") != "libx264":
            kwargs["codec"] = "libx264"
        if "preset" not in kwargs:
            kwargs["preset"] = "fast"

    return kwargs


def gpu_write_videofile(clip, output_path: str, **kwargs):
    """
    Drop-in replacement for clip.write_videofile() that uses
    hardware encoding when available, with automatic CPU fallback.
    """
    backend = detect_gpu_backend()

    if backend != "cpu":
        hw_kwargs = _apply_hw_params(dict(kwargs), backend)
        label = {"vaapi": "VAAPI (AMD/Intel)", "nvenc": "NVENC (NVIDIA)",
                 "videotoolbox": "VideoToolbox (macOS)"}[backend]
        print(f"[GPU] Rendering with {label} → {output_path}")
        try:
            clip.write_videofile(str(output_path), **hw_kwargs)
            return
        except Exception as e:
            print(f"[GPU] ⚠️ {label} encoding failed, falling back to CPU: {e}")

    # CPU fallback
    kwargs.pop("ffmpeg_params", None)
    if kwargs.get("codec") != "libx264":
        kwargs["codec"] = "libx264"
    if "preset" not in kwargs:
        kwargs["preset"] = "fast"

    print(f"[GPU] Rendering with CPU (libx264) → {output_path}")
    clip.write_videofile(str(output_path), **kwargs)
