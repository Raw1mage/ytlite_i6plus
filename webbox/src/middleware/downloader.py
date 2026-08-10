
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
        """Download a video. Returns (ok, error, final_path).

        fmt: 'mp3' or 'mp4'

        final_path is what yt-dlp actually wrote, read back from its own report
        rather than reconstructed by us. That matters now that the name is
        derived from the title: the caller can no longer rebuild the path from
        the video_id, and a guessed path that happens not to exist would be
        indistinguishable from a download that failed. On failure final_path is
        None -- never a plausible-looking path we made up.
        """
        target_dir = output_dir or self.download_dir

        # Filename comes from the TITLE, with the video id as an automatic
        # fallback. The comma in %(title,id)s is yt-dlp's alternate-field
        # syntax: if title is missing or empty it uses id instead. Writing a
        # bare %(title)s would produce 'NA.<ext>' for every untitled video, and
        # they would overwrite each other -- one shared filename for an
        # unbounded number of distinct videos.
        #
        # .59s truncates to 59 CHARACTERS (yt-dlp counts characters, not
        # bytes), which is the measured limit rather than a guessed one. ext4
        # caps a filename at 255 BYTES, and the binding case is a 4-byte
        # character plus yt-dlp's longest intermediate suffix:
        #     emoji x100 -> final 240B, worst temp '.f251.webm.part' 251B  <= 255
        #     CJK   x100 -> final 181B, worst temp 192B
        # Raising 59 requires re-running that emoji measurement; the CJK case
        # alone would wrongly suggest there is plenty of room.
        # (trim_file_name was rejected: it also counts characters, and measured
        # here it truncates the extension off the end of the name.)
        #
        # windowsfilenames=True maps the characters a filesystem cannot take
        # onto their full-width equivalents (: " / -> ： ＂ ⧸) instead of
        # deleting them, so a title stays readable rather than losing its
        # punctuation silently.
        ydl_opts = {
            'outtmpl': f'{target_dir}/%(title,id).59s.%(ext)s',
            'windowsfilenames': True,
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
            final_path = await loop.run_in_executor(None, self._run_yt_dlp, ydl_opts, url)
            return True, None, final_path
        except Exception as e:
            return False, str(e), None

    # ext4 caps a single filename at 255 BYTES. Measured in this container by
    # creating files, not by reading documentation: 255B is created, 256B
    # raises OSError.
    _NAME_MAX_BYTES = 255
    # The longest thing yt-dlp appends to the stem before the postprocessor
    # produces the final name. Everything shorter is covered by budgeting for
    # this one.
    _LONGEST_TEMP_SUFFIX = '.f251.webm.part'

    @staticmethod
    def _fit_bytes(s, budget):
        """Truncate s so it encodes to at most `budget` bytes, never mid-character.

        A naive s.encode()[:budget] splits multi-byte characters: measured, a
        run of 4-byte emoji cut at 255 bytes raises UnicodeDecodeError, and the
        'ignore' error handler papers over it by silently dropping the partial
        character. Dropping whole characters from the end is the same outcome
        without pretending a decode error did not happen.
        """
        if budget <= 0:
            return ''
        b = s.encode('utf-8')
        if len(b) <= budget:
            return s
        out = []
        used = 0
        for ch in s:
            n = len(ch.encode('utf-8'))
            if used + n > budget:
                break
            out.append(ch)
            used += n
        return ''.join(out)

    @classmethod
    def _free_name(cls, target_dir, stem, ext_hint):
        """Return a stem that does not collide, appending ' (2)', ' (3)', ...

        Two different videos can share a title -- the name is derived from a
        field YouTube does not make unique. Measured before this existed: two
        distinct videos written to one path left ONE file (1912364B then
        2017196B, so the second really did overwrite the first rather than
        being skipped), and yt-dlp does not prevent it -- params['overwrites']
        defaults to None. The first video's audio was simply gone.

        The collision test looks at any extension, not just the expected one:
        the download passes through intermediate names (.webm, .part, .f251...)
        before the postprocessor produces the final .mp3, so matching only
        '<stem>.mp3' would let an in-flight download of the same title collide.

        THE SUFFIX IS SUBTRACTED FROM THE TITLE'S BUDGET, NOT ADDED AFTER IT.
        outtmpl's .59s truncates to 59 CHARACTERS, and a 4-byte emoji makes
        that 236 bytes, so appending the suffix overflows:

            emoji x200, no suffix     final 240B   worst temp 251B   ok
            emoji x200, ' (2)'        final 244B   worst temp 255B   ok, at the edge
            emoji x200, ' (999)'      final 246B   worst temp 257B   OVER
            emoji x200, ' (<epoch>)'  final 253B   worst temp 264B   OVER

        The failure would land in os.rename inside the postprocessor -- after
        the bytes are already downloaded, so the user pays the full bandwidth
        cost and then gets an OSError. Budgeting costs nothing by comparison,
        and only bites the pathological case: a CJK title at ' (999)' is 198B
        and is never touched by this.
        """
        def taken(s):
            try:
                names = os.listdir(target_dir)
            except OSError as e:
                # "I could not look" is NOT "nothing is there". Reporting False
                # here would hand back the unsuffixed stem and overwrite a file
                # we simply failed to see. Treating it as taken is the safe
                # direction: at worst we add a suffix nobody needed.
                print('[Downloader] cannot list %r (%s); treating names as taken'
                      % (target_dir, type(e).__name__), flush=True)
                raise
            return any(n == s or n.startswith(s + '.') for n in names)

        def fits(s):
            return len((s + cls._LONGEST_TEMP_SUFFIX).encode('utf-8')) <= cls._NAME_MAX_BYTES

        def budgeted(base, suffix):
            """base truncated so that base+suffix+longest-temp-suffix fits."""
            room = (cls._NAME_MAX_BYTES
                    - len(cls._LONGEST_TEMP_SUFFIX.encode('utf-8'))
                    - len(suffix.encode('utf-8')))
            return cls._fit_bytes(base, room) + suffix

        try:
            plain = budgeted(stem, '')
            if not taken(plain):
                return plain
            # Bounded: an unbounded loop here would spin on a directory whose
            # contents keep changing under us.
            for i in range(2, 1000):
                cand = budgeted(stem, ' (%d)' % i)
                if not taken(cand):
                    return cand
            return budgeted(stem, ' (%d)' % int(time.time()))
        except OSError:
            # Directory unreadable (see taken()). Fall back to a name that
            # cannot collide with anything, still inside the byte budget.
            return budgeted(stem, ' (%d)' % int(time.time()))

    def _run_yt_dlp(self, opts, url):
        """Run the download and return the path yt-dlp reports writing.

        Two phases on ONE YoutubeDL instance: fetch the metadata, work out the
        name it would use, rewrite outtmpl if that name is taken, then download.
        Measured: extract_info(download=False) costs 0.90s and
        process_ie_result reuses that info without a second network fetch, so
        the collision check does not double the request count.

        One instance rather than two on purpose -- a second YoutubeDL fed the
        first one's info dict did fail here with a 403, and while a control
        proved that particular 403 was transient rate limiting rather than a
        structural problem, mutating params on the instance that already holds
        the extractor state avoids the question entirely.

        The final path is read from info['requested_downloads'][0]['filepath'],
        which is MEASURED, not inferred: the top-level info dict has no
        'filepath' key at all after a postprocessed download (verified on this
        container -- top-level filepath is None while requested_downloads[0]
        carries the real post-conversion .mp3 path). Reading the wrong one
        would hand back None on every success.

        Returns None if yt-dlp reports no path. The caller must treat that as
        'unknown', not as a reason to guess: an invented path is exactly the
        failure this return value exists to prevent.
        """
        target_dir = os.path.dirname(opts['outtmpl'])

        with yt_dlp.YoutubeDL(opts) as ydl:
            meta = ydl.extract_info(url, download=False)
            if meta:
                planned = os.path.basename(ydl.prepare_filename(meta))
                stem = os.path.splitext(planned)[0]
                free = self._free_name(target_dir, stem, None)
                if free != stem:
                    # A literal name now, so any '%' inside the title must be
                    # doubled or yt-dlp reads it as a field specifier. (Measured:
                    # an unescaped '100% Real' happens to survive, but that is
                    # the parser failing to match a field, not a guarantee.)
                    literal = free.replace('%', '%%')
                    opts_tmpl = '%s/%s.%%(ext)s' % (target_dir, literal)
                    ydl.params['outtmpl'] = {'default': opts_tmpl}
                    print('[Downloader] name taken; using %r' % (free,), flush=True)
                info = ydl.process_ie_result(meta, download=True)
            else:
                info = ydl.extract_info(url, download=True)

        if not info:
            return None
        reqs = info.get('requested_downloads') or []
        if reqs:
            p = reqs[0].get('filepath')
            if p:
                return p
        # Older/other shapes put it at the top level; try that before giving up.
        return info.get('filepath') or None

