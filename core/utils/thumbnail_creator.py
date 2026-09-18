import os
import io
import subprocess
from pathlib import Path
from PIL import Image
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment
project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(project_root / "secrets" / ".env")

# Primary model: Google Nano Banana 2 Lite (Gemini 3.1 Flash Lite Image)
# Fallback model: Google Nano Banana 2 (Gemini 3.1 Flash Image)
PRIMARY_MODEL = "gemini-3.1-flash-lite-image"
FALLBACK_MODEL = "gemini-3.1-flash-image"


def get_gemini_client() -> genai.Client:
    """Instantiates and returns the Google GenAI client using GEMINI_API_KEY."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY in secrets/.env")
    return genai.Client(api_key=api_key)


def extract_starting_frame(video_path: str | Path, output_image_path: str | Path | None = None) -> Image.Image:
    """
    Extracts the starting frame from a video file using FFmpeg.
    If output_image_path is provided, saves the image to disk.
    Returns the PIL Image object.
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    cmd = [
        "ffmpeg",
        "-y",
        "-ss", "00:00:00.100",
        "-i", str(video_path),
        "-vframes", "1",
        "-f", "image2pipe",
        "-vcodec", "png",
        "-"
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    if not result.stdout:
        raise RuntimeError(f"FFmpeg failed to extract frame from {video_path}: {result.stderr.decode('utf-8', errors='ignore')}")

    img = Image.open(io.BytesIO(result.stdout)).convert("RGB")

    if output_image_path:
        out_p = Path(output_image_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_p)

    return img


def generate_thumbnail(
    title: str,
    script: str,
    starting_frame: str | Path | Image.Image | bytes,
    output_path: str | Path | None = None,
    aspect_ratio: str = "auto",
    client: genai.Client | None = None
) -> Path | Image.Image:
    """
    Generates a high-CTR YouTube thumbnail using Google Nano Banana 2 Lite (gemini-3.1-flash-lite-image).
    
    The generation is visually anchored in the video's starting frame, title, and script
    so viewers get an engaging preview that accurately reflects the video content without clickbait.

    Args:
        title: Title of the video.
        script: Full script, narration, or narrative summary of the video.
        starting_frame: Video path (.mp4), image path, PIL Image, or image bytes.
        output_path: Destination path to save the generated thumbnail (e.g. 'output/thumbnail.png').
        aspect_ratio: Image aspect ratio ('auto', '16:9', '9:16'). Defaults to 'auto' based on video/frame dimensions.
        client: Optional pre-configured Google GenAI client.

    Returns:
        Path to the saved thumbnail file if output_path was provided, otherwise the PIL Image.
    """
    if client is None:
        client = get_gemini_client()

    # Load and normalize reference frame image
    if isinstance(starting_frame, (str, Path)):
        ref_path = Path(starting_frame)
        if not ref_path.exists():
            raise FileNotFoundError(f"Starting frame or video not found at: {ref_path}")
        if ref_path.suffix.lower() in [".mp4", ".mov", ".mkv", ".webm"]:
            ref_image = extract_starting_frame(ref_path)
        else:
            ref_image = Image.open(ref_path).convert("RGB")
    elif isinstance(starting_frame, bytes):
        ref_image = Image.open(io.BytesIO(starting_frame)).convert("RGB")
    elif isinstance(starting_frame, Image.Image):
        ref_image = starting_frame.convert("RGB")
    else:
        raise TypeError(f"Unsupported starting_frame type: {type(starting_frame)}")

    # Determine aspect ratio automatically if requested
    if aspect_ratio == "auto" or not aspect_ratio:
        if ref_image.height > ref_image.width:
            aspect_ratio = "9:16"
        else:
            aspect_ratio = "16:9"

    prompt = (
        f"You are an expert YouTube thumbnail designer.\n"
        f"Create a captivating, high-CTR thumbnail for a video titled '{title}'.\n\n"
        f"Video Script / Content Summary:\n"
        f"\"\"\"{script.strip()}\"\"\"\n\n"
        f"CRITICAL DESIGN REQUIREMENTS:\n"
        f"1. Authenticity (Zero Clickbait): The thumbnail MUST remain grounded in the visual context, "
        f"subject matter, art style, and emotional tone of the provided starting frame image. "
        f"The viewer must recognize a direct continuity between the thumbnail and the video.\n"
        f"2. Visual Impact & Elevation: Enhance the scene with cinematic lighting, dynamic focal emphasis, "
        f"and strong visual contrast so it stands out prominently on both mobile feeds and desktop screens.\n"
        f"3. Clean Composition: Keep the main subject bold and uncluttered. Avoid chaotic small elements or random unreadable text.\n"
        f"4. Deliver an image formatted for the requested aspect ratio."
    )

    models_to_try = [PRIMARY_MODEL, FALLBACK_MODEL]
    last_error = None

    for model_name in models_to_try:
        try:
            print(f"[Thumbnail Creator] Generating thumbnail with {model_name} (Aspect Ratio: {aspect_ratio})...")
            config_kwargs = {"response_modalities": ["IMAGE"]}
            if aspect_ratio:
                config_kwargs["image_config"] = types.ImageConfig(aspect_ratio=aspect_ratio)

            response = client.models.generate_content(
                model=model_name,
                contents=[ref_image, prompt],
                config=types.GenerateContentConfig(**config_kwargs)
            )

            generated_image = None
            if response.parts:
                for part in response.parts:
                    if getattr(part, "inline_data", None) is not None:
                        generated_image = part.as_image()
                        break

            if generated_image is None and hasattr(response, "candidates") and response.candidates:
                for cand in response.candidates:
                    if hasattr(cand, "content") and cand.content and hasattr(cand.content, "parts"):
                        for p in cand.content.parts:
                            if getattr(p, "inline_data", None) is not None:
                                generated_image = p.as_image()
                                break
                    if generated_image:
                        break

            if generated_image:
                if output_path:
                    out_p = Path(output_path)
                    out_p.parent.mkdir(parents=True, exist_ok=True)
                    generated_image.save(out_p)
                    print(f"[Thumbnail Creator] Thumbnail successfully saved to {out_p}")
                    return out_p
                return generated_image
            else:
                raise RuntimeError("No image was returned in the Gemini response parts.")

        except Exception as e:
            print(f"[Thumbnail Creator] Warning: Generation failed with {model_name}: {e}")
            last_error = e

    raise RuntimeError(f"Failed to generate thumbnail with available models: {last_error}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate video thumbnail using Google Nano Banana 2 Lite.")
    parser.add_argument("--title", type=str, required=True, help="Video title")
    parser.add_argument("--script", type=str, required=True, help="Video script or description")
    parser.add_argument("--frame", type=str, required=True, help="Path to starting frame image or video file")
    parser.add_argument("--out", type=str, default="output/thumbnail.png", help="Output thumbnail path")
    parser.add_argument("--aspect", type=str, default="16:9", help="Aspect ratio (e.g. 16:9, 9:16)")

    args = parser.parse_args()

    frame_path = Path(args.frame)
    if frame_path.suffix.lower() in [".mp4", ".mov", ".mkv", ".webm"]:
        print(f"[Thumbnail Creator] Extracting starting frame from video: {frame_path}")
        temp_frame_path = Path("output/temp_starting_frame.png")
        input_frame = extract_starting_frame(frame_path, temp_frame_path)
    else:
        input_frame = frame_path

    result_path = generate_thumbnail(
        title=args.title,
        script=args.script,
        starting_frame=input_frame,
        output_path=args.out,
        aspect_ratio=args.aspect
    )
    print(f"Thumbnail created at: {result_path}")
