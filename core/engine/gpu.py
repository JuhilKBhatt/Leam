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


def _apply_hw_params(kwargs: dict, backend: str) -> dict:
    """
    Mutate kwargs for write_videofile to use the detected
    hardware encoder.  Returns the (possibly modified) dict.
    """
    if backend == "vaapi":
        kwargs["codec"] = "h264_vaapi"
        kwargs.pop("preset", None)          # VAAPI ignores x264 presets
        vaapi_params = [
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


import os

def _create_vaapi_wrapper():
    """Create a bash wrapper to inject -vaapi_device before MoviePy's input args."""
    global _working_vaapi_device
    device = _working_vaapi_device or "/dev/dri/renderD128"
    wrapper_path = "/tmp/ffmpeg_vaapi_wrapper.sh"
    with open(wrapper_path, "w") as f:
        f.write('#!/bin/bash\n')
        f.write(f'exec ffmpeg -vaapi_device {device} "$@"\n')
    os.chmod(wrapper_path, 0o755)
    return wrapper_path

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
        
        original_exe = os.environ.get("IMAGEIO_FFMPEG_EXE")
        import moviepy.config as conf
        original_moviepy_exe = conf.FFMPEG_BINARY
        
        target_exe = shutil.which("ffmpeg")
        if backend == "vaapi":
            target_exe = _create_vaapi_wrapper()

        if target_exe:
            os.environ["IMAGEIO_FFMPEG_EXE"] = target_exe
            conf.FFMPEG_BINARY = target_exe

        print(f"[GPU] Rendering with {label} → {output_path}")
        success = False
        try:
            clip.write_videofile(str(output_path), **hw_kwargs)
            success = True
        except Exception as e:
            print(f"[GPU] ⚠️ {label} encoding failed, falling back to CPU: {e}")
        finally:
            if original_exe:
                os.environ["IMAGEIO_FFMPEG_EXE"] = original_exe
            elif "IMAGEIO_FFMPEG_EXE" in os.environ:
                del os.environ["IMAGEIO_FFMPEG_EXE"]
            conf.FFMPEG_BINARY = original_moviepy_exe

    # CPU fallback
    kwargs.pop("ffmpeg_params", None)
    if kwargs.get("codec") != "libx264":
        kwargs["codec"] = "libx264"
    if "preset" not in kwargs:
        kwargs["preset"] = "fast"

    print(f"[GPU] Rendering with CPU (libx264) → {output_path}")
    clip.write_videofile(str(output_path), **kwargs)
