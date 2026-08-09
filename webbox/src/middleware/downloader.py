
import yt_dlp
import asyncio
import os
import time

class Downloader:
    def __init__(self, download_dir):
        self.download_dir = download_dir
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

    async def download(self, video_id, fmt, job_id, progress_callback, output_dir=None):
        """
        Downloads a video using yt-dlp.
        fmt: 'mp3' or 'mp4'
        """
        target_dir = output_dir or self.download_dir
        
        # Base options
        ydl_opts = {
            # Use video_id as filename to allow caching/reuse
            'outtmpl': f'{target_dir}/{video_id}.%(ext)s',
            'progress_hooks': [lambda d: progress_callback(job_id, d)],
            'quiet': True,
            'no_warnings': True,
        }

        if fmt == 'mp3':
            ydl_opts.update({
                'format': 'bestaudio/best',
                # Fetch the thumbnail so EmbedThumbnail has something to embed. Without
                # this the embed postprocessor has no input and silently does nothing --
                # and with quiet/no_warnings on, the download still reports success.
                'writethumbnail': True,
                'postprocessors': [
                    {
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    },
                    # ORDER IS LOAD-BEARING: extract audio -> write tags -> embed cover.
                    # FFmpegMetadata maps yt-dlp fields onto ID3 tags. Its artist rule is
                    # ('artist', 'artists', 'creator', 'creators', 'uploader', 'uploader_id')
                    # (yt_dlp/postprocessor/ffmpeg.py:751), so an ordinary YouTube video --
                    # which carries no 'artist' at all -- still gets the channel name via
                    # the 'uploader' fallback. That is why no parse_metadata rule is needed.
                    {
                        'key': 'FFmpegMetadata',
                        'add_metadata': True,
                    },
                    # For mp3 this runs ffmpeg directly (embedthumbnail.py:90-96), unlike
                    # the ogg/opus/flac branch which hard-requires mutagen. mutagen is NOT
                    # installed here and is NOT needed for this path.
                    {
                        'key': 'EmbedThumbnail',
                        'already_have_thumbnail': False,
                    },
                ],
            })
        else: # mp4
            ydl_opts.update({
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                # Ensure we get a merge if video+audio are separate
                'merge_output_format': 'mp4',
            })

        url = f"https://www.youtube.com/watch?v={video_id}"

        loop = asyncio.get_event_loop()
        try:
            # Run blocking code in executor
            await loop.run_in_executor(None, self._run_yt_dlp, ydl_opts, url)
            return True, None
        except Exception as e:
            return False, str(e)

    def _run_yt_dlp(self, opts, url):
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

