import os
import traceback
from typing import Optional, Tuple

import yt_dlp
from config import Config


class Downloader:
    @staticmethod
    def download_url(url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Download audio from a video URL using yt-dlp and ffmpeg.

        Returns:
            (filepath, title, error_message)

            - filepath: full path to the downloaded .mp3 file, or None on error
            - title:    video title if available, else 'Unknown Title' or None on error
            - error_message: None if success, otherwise a string describing the error
        """

        # Ensure the upload folder exists
        try:
            os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        except Exception as e:
            err = f"Failed to create upload folder '{Config.UPLOAD_FOLDER}': {e}"
            print(err)
            return None, None, err

        # yt-dlp options
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(Config.UPLOAD_FOLDER, "%(id)s.%(ext)s"),
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            # For debugging, set quiet=False and no_warnings=False
            # For debugging, set quiet=False and no_warnings=False
            "quiet": True,
            "no_warnings": True,
            # "cookiesfrombrowser": ("chrome",), # Disabled due to lock errors
        }

        # Check for cookies.txt
        cookies_path = os.path.join(os.getcwd(), "cookies.txt")
        if os.path.isfile(cookies_path):
            ydl_opts["cookiefile"] = cookies_path
            print(f"Using cookies from: {cookies_path}")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Download the video and get info dict
                info = ydl.extract_info(url, download=True)

                # Let yt-dlp tell us the base filename it used
                original_path = ydl.prepare_filename(info)
                base, _ = os.path.splitext(original_path)
                filepath = base + ".mp3"  # ffmpeg output

                title = info.get("title", "Unknown Title")

                # Double-check file actually exists
                if not os.path.isfile(filepath):
                    err = f"Expected output file not found: {filepath}"
                    print(err)
                    return None, None, err

                return filepath, title, None

        except yt_dlp.utils.DownloadError as e:
            # Typical download errors: network, URL invalid, blocked, etc.
            traceback.print_exc()
            err = f"DownloadError: {e}"
            print(err)
            return None, None, err

        except Exception as e:
            # Anything else: permissions, filesystem, unexpected issues
            traceback.print_exc()
            err = f"Unexpected error: {e}"
            print(err)
            return None, None, err
