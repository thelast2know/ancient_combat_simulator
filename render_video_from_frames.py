"""Render video from saved PNG frames - standalone post-processing tool"""
import cv2
import glob
import argparse
from pathlib import Path
from datetime import datetime


def render_video_from_frames(frames_dir, output_video, fps=30):
    """Create MP4 video from PNG frames
    
    Args:
        frames_dir: Directory containing frame_*.png files
        output_video: Output MP4 file path
        fps: Playback frames per second (default 30)
    """
    frames_dir = Path(frames_dir)
    output_video = Path(output_video)
    
    # Find all PNG frames
    frame_files = sorted(glob.glob(str(frames_dir / "frame_*.png")))
    if not frame_files:
        print(f"ERROR: No frames found in {frames_dir}")
        return False
    
    print(f"Found {len(frame_files)} PNG frames")
    
    # Read first frame to get dimensions
    first_frame = cv2.imread(frame_files[0])
    if first_frame is None:
        print(f"ERROR: Could not read first frame: {frame_files[0]}")
        return False
    
    height, width = first_frame.shape[:2]
    print(f"Frame dimensions: {width}x{height}")
    
    # Create video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_video), fourcc, fps, (width, height))
    
    if not out.isOpened():
        print(f"ERROR: Could not open video writer for {output_video}")
        return False
    
    # Write all frames
    for i, frame_file in enumerate(frame_files):
        frame = cv2.imread(frame_file)
        if frame is None:
            print(f"WARNING: Could not read {frame_file}")
            continue
        out.write(frame)
        if (i + 1) % 50 == 0:
            print(f"  Wrote {i + 1}/{len(frame_files)} frames")
    
    out.release()
    
    video_size_mb = output_video.stat().st_size / (1024 * 1024)
    print("[OK] Video saved: " + str(output_video))
    print(f"  Frames: {len(frame_files)}")
    print(f"  Duration: {len(frame_files) / fps:.1f} seconds")
    print(f"  FPS: {fps}")
    print(f"  Size: {video_size_mb:.1f} MB")
    
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert PNG frames to MP4 video')
    parser.add_argument(
        '--input', '-i',
        default='debug/frames',
        help='Input directory containing frame_*.png files (default: debug/frames)'
    )
    parser.add_argument(
        '--output', '-o',
        default=None,
        help='Output MP4 file path (default: output_videos/phase2_TIMESTAMP.mp4)'
    )
    parser.add_argument(
        '--fps',
        type=int,
        default=30,
        help='Playback frames per second (default: 30)'
    )
    
    args = parser.parse_args()
    
    # Generate timestamped output filename if not provided
    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f'output_videos/phase2_fixed_{timestamp}.mp4'
    
    # Create output directory if needed
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print("Converting frames to video...")
    print(f"  Input: {args.input}")
    print(f"  Output: {args.output}")
    print(f"  FPS: {args.fps}")
    
    if render_video_from_frames(args.input, args.output, fps=args.fps):
        print("\n[OK] Video rendering complete!")
    else:
        print("\n[FAILED] Video rendering failed")
