"""
Loop video to SRT streaming url infinitely. Video must be called "video.mp4" in same folder or changed in code.

Usage:
    python stream.py [stream_url]

If stream_url is not provided, it will be read from the SRT variable in .env file.

Example:
    python stream.py "srt://localhost:8890?streamid=publish:CHANNEL_NAME:USERNAME:STREAM_KEY&pkt_size=1316"
    
    Or create a .env file with:
    SRT=srt://localhost:8890?streamid=publish:CHANNEL_NAME:USERNAME:STREAM_KEY&pkt_size=1316
"""

import subprocess
import sys
import os
import signal
import time
from dotenv import load_dotenv

VIDEO_FILE = "video.mp4"

FFMPEG_SETTINGS = {

    # Video
    "video_codec":    "libx264",
    "preset":         "veryfast",
    "tune":           "zerolatency",
    "crf":            "23",
    "video_bitrate":  "2500k",
    "bufsize":        "5000k",
    "pix_fmt":        "yuv420p",
    "g":              "60",

    # Audio
    "audio_codec":    "aac",
    "audio_bitrate":  "160k",
    "audio_rate":     "44100",
    "audio_channels": "2",

    # Output
    "format":         "mpegts",
}


def check_ffmpeg():
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except FileNotFoundError:
        print(
            "ERROR: ffmpeg not found. Please install ffmpeg and ensure it is in your PATH.")
        sys.exit(1)


def build_command(stream_url: str) -> list[str]:
    s = FFMPEG_SETTINGS
    return [
        "ffmpeg",
        "-re",
        "-stream_loop", "-1",
        "-i", VIDEO_FILE,

        # Video encoding
        "-c:v",       s["video_codec"],
        "-preset",    s["preset"],
        "-tune",      s["tune"],
        "-crf",       s["crf"],
        "-maxrate",   s["video_bitrate"],
        "-bufsize",   s["bufsize"],
        "-pix_fmt",   s["pix_fmt"],
        "-g",         s["g"],

        # Audio encoding
        "-c:a",       s["audio_codec"],
        "-b:a",       s["audio_bitrate"],
        "-ar",        s["audio_rate"],
        "-ac",        s["audio_channels"],

        # Output
        "-f",         s["format"],
        stream_url,
    ]


def stream(stream_url: str):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    video_path = os.path.join(script_dir, VIDEO_FILE)

    if not os.path.isfile(video_path):
        print(f"ERROR: Video file not found: {video_path}")
        sys.exit(1)

    os.chdir(script_dir)

    cmd = build_command(stream_url)
    print("Starting stream …")
    print("URL:", stream_url)
    print("Press Ctrl+C to stop.\n")

    attempt = 0
    while True:
        attempt += 1
        if attempt > 1:
            print(f"\nReconnecting (attempt {attempt}) …")
            time.sleep(3)

        proc = subprocess.Popen(cmd)

        try:
            proc.wait()
        except KeyboardInterrupt:
            print("\nStopping stream …")
            proc.send_signal(signal.SIGINT)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            print("Stream stopped.")
            sys.exit(0)

        ret = proc.returncode
        if ret == 0:
            print("FFmpeg exited cleanly.")
            break
        else:
            print(f"FFmpeg exited with code {ret}. Will retry …")


if __name__ == "__main__":
    check_ffmpeg()

    if len(sys.argv) == 2:
        stream_url = sys.argv[1]
    else:
        load_dotenv()
        stream_url = os.getenv("SRT")
        if not stream_url:
            print("ERROR: No stream URL provided.")
            print("Either pass it as an argument or set SRT in .env file.\n")
            print(__doc__)
            sys.exit(1)

    stream(stream_url)
