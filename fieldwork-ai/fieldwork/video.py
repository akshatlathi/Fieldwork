"""Bounded analysis-video preparation; original evidence is never modified."""
from pathlib import Path
import subprocess
import tempfile

import cv2

INLINE_LIMIT = 20 * 1024 * 1024
SOURCE_LIMIT = 50 * 1024 * 1024
MAX_SECONDS = 60


class VideoInputError(ValueError):
    pass


def validate_video(path: Path) -> float:
    if path.stat().st_size > SOURCE_LIMIT:
        raise VideoInputError("Video is too large. Choose a clip under 50 MB and 60 seconds.")
    cap = cv2.VideoCapture(str(path))
    try:
        fps, count = cap.get(cv2.CAP_PROP_FPS), cap.get(cv2.CAP_PROP_FRAME_COUNT)
        if not cap.isOpened() or fps <= 0 or count <= 0:
            raise VideoInputError("Could not read this video. Try an MP4 or WebM clip.")
        duration = count / fps
        if duration > MAX_SECONDS:
            raise VideoInputError("Video is too long. Choose a clip under 60 seconds.")
        return duration
    finally:
        cap.release()


def inline_video(path: Path) -> tuple[bytes, str]:
    """Keep short/small inputs; compress larger ones with rotation and audio intact.

    Full-resolution evidence frames are extracted separately from the original.
    FFmpeg's default autorotation bakes the display transform into the proxy.
    """
    validate_video(path)
    if path.stat().st_size <= INLINE_LIMIT and path.suffix.lower() in (".mp4", ".webm"):
        return path.read_bytes(), "video/webm" if path.suffix.lower() == ".webm" else "video/mp4"
    import imageio_ffmpeg
    with tempfile.TemporaryDirectory(prefix="fieldwork-video-") as temp:
        output = Path(temp) / "analysis.mp4"
        command = [imageio_ffmpeg.get_ffmpeg_exe(), "-nostdin", "-hide_banner", "-loglevel", "error",
                   "-i", str(path), "-map", "0:v:0", "-map", "0:a:0?",
                   "-vf", "scale=w='min(1280,iw)':h='min(1280,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2",
                   "-r", "24", "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                   "-maxrate", "1800k", "-bufsize", "3600k", "-pix_fmt", "yuv420p",
                   "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", "-map_metadata", "-1", str(output)]
        try:
            subprocess.run(command, check=True, capture_output=True, timeout=120)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
            raise VideoInputError("Could not prepare this video. Try a shorter MP4 or use photos.") from exc
        if not output.is_file() or output.stat().st_size > INLINE_LIMIT:
            raise VideoInputError("Video is still too large after preparation. Try a shorter clip or photos.")
        validate_video(output)
        return output.read_bytes(), "video/mp4"
