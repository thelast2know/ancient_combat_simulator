#!/usr/bin/env python3
"""Render smooth video from frames at 15 FPS (slower, smoother playback)."""
import subprocess
from pathlib import Path
from datetime import datetime


def render_smooth_video(frames_dir='debug/frames_smooth', fps=15):
    """Render MP4 video from PNG frames at specified FPS.

    Args:
        frames_dir: Directory containing frame_XXXX.png files
        fps: Frames per second (default 15 for smooth slow-motion)
    """
    frames_path = Path(frames_dir)
    output_dir = Path('output_videos')
    output_dir.mkdir(exist_ok=True)

    # Timestamped filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f'phase2_smooth_{timestamp}.mp4'

    # Check frame count
    frames = sorted(frames_path.glob('frame_*.png'))
    frame_count = len(frames)

    if frame_count == 0:
        print("[ERROR] No frames found in directory!")
        return

    # Get frame dimensions
    import cv2
    first_frame = cv2.imread(str(frames[0]))
    height, width = first_frame.shape[:2]

    print("=" * 80)
    print("RENDERING SMOOTH VIDEO")
    print("=" * 80)
    print(f"Input directory: {frames_dir}")
    print(f"Output file: {output_file}")
    print(f"Frames: {frame_count}")
    print(f"Frame rate: {fps} FPS")
    print(f"Video duration: {frame_count/fps:.1f} seconds")
    print(f"Resolution: {width}x{height}")
    print()
    print("Encoding with ffmpeg...")
    print()

    # FFmpeg command for MP4 encoding
    cmd = [
        'ffmpeg',
        '-framerate', str(fps),
        '-i', str(frames_path / 'frame_%04d.png'),
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-crf', '18',  # Quality (lower = better, 18 is high quality)
        str(output_file)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            file_size_mb = output_file.stat().st_size / (1024 * 1024)
            print()
            print("=" * 80)
            print("[OK] Video rendering complete!")
            print("=" * 80)
            print(f"Output: {output_file}")
            print(f"  Frames: {frame_count}")
            print(f"  Duration: {frame_count/fps:.1f} seconds")
            print(f"  FPS: {fps}")
            print(f"  Size: {file_size_mb:.1f} MB")
            print()
        else:
            print("[ERROR] ffmpeg failed:")
            print(result.stderr)

    except FileNotFoundError:
        print("[ERROR] ffmpeg not found. Please install it:")
        print("  Windows: choco install ffmpeg")
        print("  macOS: brew install ffmpeg")
        print("  Linux: sudo apt install ffmpeg")


if __name__ == '__main__':
    render_smooth_video(frames_dir='debug/frames_smooth', fps=15)
