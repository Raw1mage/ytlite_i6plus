
import asyncio
import uuid
import time
import os
import shutil
import struct
from downloader import Downloader

# Media extensions yt-dlp may produce. Anything else on disk is ignored.
MEDIA_EXTS = ('.mp3', '.mp4', '.m4a', '.webm', '.mkv', '.opus', '.aac', '.flac')
# Partial / sidecar artifacts that must never be shown as finished downloads.
PARTIAL_SUFFIXES = ('.part', '.ytdl', '.tmp', '.temp')
# Stable namespace so a rescan of the same file always yields the same job_id.
_DISK_JOB_NS = uuid.UUID('6f0d2a1e-6b1a-4c3f-9b2d-0e5a7c4d8f11')
# Status for jobs reconstructed from disk. Deliberately NOT 'completed'.
#
# On 2026-08-09 an earlier version of this scan used 'completed'. The frontend
# auto-save loop consumes exactly that status, fetched all 73 reconstructed jobs
# and then issued DELETE, destroying ~4.3GB. A history file is not a download
# this session just finished, and it must not be fed to a pipeline whose job is
# to move fresh downloads to the client and free the server copy. 'archived'
# keeps them out of every automatic consumer while still being renderable.
ARCHIVED_STATUS = 'archived'

# How much of an ID3v2 tag we are willing to read looking for TIT2. Cover art
# lives in the same tag and is often megabytes; the text frames sit before it.
_ID3_SCAN_LIMIT = 256 * 1024


def read_id3_title(path):
    """Return (title_or_None, reason) for an mp3 on disk.

    Every way of NOT getting a title returns a DISTINCT reason string. That is
    the whole point of this function's shape: if 'file unreadable', 'not an
    mp3', 'tag present but no TIT2' and 'TIT2 present but empty' all collapsed
    into '' , the caller's `title or stem` fallback would look correct in every
    case while having no discriminating power at all -- it could never report
    which of those actually happened. Callers may still treat them alike; the
    logs must be able to tell them apart.

    Pure stdlib on purpose. Measured on the live container over 60 real files:
    0.508 ms/file (30.5 ms total, ~305 ms extrapolated to 600 files), versus
    129.6 ms/file for an ffprobe subprocess (~77.7 s at 600 files) -- 255x.
    At 305 ms the startup cost that would have justified a lazy/background/
    mutagen design simply is not there, and each of those alternatives carries
    a real cost: lazy slows the 2-second poll endpoint, a background thread
    races get_jobs(), mutagen is a new dependency.
    Cross-checked against ffprobe on 8 files: 8/8 identical.
    """
    try:
        with open(path, 'rb') as f:
            head = f.read(10)
            if len(head) < 10:
                return None, 'TOO_SHORT'
            if head[:3] != b'ID3':
                return None, 'NO_ID3'
            ver = head[3]
            sz = head[6:10]
            if any(b & 0x80 for b in sz):
                return None, 'BAD_SIZE'
            size = (sz[0] << 21) | (sz[1] << 14) | (sz[2] << 7) | sz[3]
            body = f.read(min(size, _ID3_SCAN_LIMIT))
    except OSError as e:
        return None, 'IO_ERROR:%s' % type(e).__name__

    i, n = 0, len(body)
    while i + 10 <= n:
        fid = body[i:i + 4]
        if fid == b'\x00\x00\x00\x00':
            return None, 'NO_TIT2'  # reached the padding
        raw = body[i + 4:i + 8]
        if ver >= 4:
            if any(b & 0x80 for b in raw):
                return None, 'BAD_FRAME_SIZE'
            fsize = (raw[0] << 21) | (raw[1] << 14) | (raw[2] << 7) | raw[3]
        else:
            fsize = struct.unpack('>I', raw)[0]
        if fsize <= 0 or i + 10 + fsize > n:
            return None, 'TRUNCATED'
        if fid == b'TIT2':
            data = body[i + 10:i + 10 + fsize]
            if not data:
                return None, 'EMPTY_FRAME'
            enc, payload = data[0], data[1:]
            try:
                if enc == 0:
                    s = payload.decode('latin-1')
                elif enc == 1:
                    s = payload.decode('utf-16')
                elif enc == 2:
                    s = payload.decode('utf-16-be')
                elif enc == 3:
                    s = payload.decode('utf-8')
                else:
                    return None, 'BAD_ENCODING:%d' % enc
            except UnicodeDecodeError:
                return None, 'DECODE_ERROR'
            s = s.split('\x00')[0].strip()
            if not s:
                return None, 'EMPTY_VALUE'
            return s, 'OK'
        i += 10 + fsize
    return None, 'NO_TIT2'


class QueueManager:
    def __init__(self, download_dir, cache_dir):
        self.downloader = Downloader(download_dir)
        self.download_dir = download_dir
        self.cache_dir = cache_dir # Separate cache directory
        
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

        self.jobs = {} # { job_id: { ... } }
        self.queue = asyncio.Queue()
        self.active_workers = 0
        self.max_workers = 1 # Limit to 1 concurrent download for low spec

        # Disk is the source of truth: self.jobs is in-memory only and is lost on
        # every restart, so rebuild it from download_dir. Without this, previously
        # downloaded files exist on disk but are invisible in the UI forever.
        self.rescan_download_dir()

        # Start worker
        asyncio.create_task(self._worker())

    def rescan_download_dir(self):
        """Rebuild jobs for files already present in download_dir, as ARCHIVED.

        Returns the number of jobs added. Single scandir pass, O(n).

        The status is ARCHIVED_STATUS, never 'completed'. See that constant for
        why: 'completed' is the trigger the auto-save pipeline consumes, and
        feeding it history files deleted 4.3GB once already.

        NOTE on the MISSING branch below: it is UNREACHABLE from __init__, which
        calls os.makedirs(download_dir) before calling us, so by the time we run
        the directory always exists (measured, not assumed: via __init__ a
        nonexistent dir logs the ordinary "0 jobs restored" line; only a direct
        call logs MISSING). It is kept for direct callers -- a future
        rescan-on-demand endpoint, or a test -- because without it os.scandir
        would raise and a missing directory would be indistinguishable from an
        empty one. Do not cite it as a guard on the production path: there, a
        vanished download_dir is silently re-created empty by __init__.
        """
        d = self.download_dir
        if not os.path.isdir(d):
            print("[Queue] rescan: download_dir MISSING: %s (0 jobs restored)" % d, flush=True)
            return 0

        added = 0
        skipped = 0
        try:
            entries = list(os.scandir(d))
        except OSError as e:
            print("[Queue] rescan: cannot read %s: %s" % (d, e), flush=True)
            return 0

        for entry in entries:
            try:
                name = entry.name
                if name.startswith('.'):
                    skipped += 1
                    continue
                if not entry.is_file():
                    skipped += 1
                    continue
                lower = name.lower()
                if lower.endswith(PARTIAL_SUFFIXES):
                    skipped += 1
                    continue
                stem, ext = os.path.splitext(name)
                if ext.lower() not in MEDIA_EXTS:
                    skipped += 1
                    continue
                if not stem:
                    skipped += 1
                    continue

                path = entry.path
                try:
                    st = entry.stat()
                    created_at = st.st_mtime
                    size = st.st_size
                except OSError:
                    # Corrupted / vanished entry: still list it, but with no stat data.
                    created_at = time.time()
                    size = 0

                # Filenames are written as "<video_id>.<ext>"; a file that does not
                # follow that convention still gets listed, with the stem as its id.
                video_id = stem
                fmt = 'mp3' if ext.lower() == '.mp3' else 'mp4'
                job_id = str(uuid.uuid5(_DISK_JOB_NS, path))

                # The human-readable title is already inside the file: the mp3
                # postprocessor added by 7c6d51a writes ID3 tags. Reading it here is
                # what stops the UI -- and the filename the browser saves as -- from
                # showing the video_id. The stem stays as the fallback, and it is a
                # real fallback, not a cosmetic one: an empty title would make the
                # downloaded file be named ".mp3".
                title = stem
                if ext.lower() == '.mp3':
                    tag_title, tag_reason = read_id3_title(path)
                    if tag_title:
                        title = tag_title
                    elif tag_reason != 'NO_ID3':
                        # NO_ID3 is the ordinary case for a file we never tagged;
                        # anything else means the tag was there and we failed to use
                        # it, which is worth seeing in the log rather than silently
                        # falling back.
                        print("[Queue] rescan: %s -> no ID3 title (%s), using stem"
                              % (name, tag_reason), flush=True)

                if job_id in self.jobs:
                    continue

                self.jobs[job_id] = {
                    'job_id': job_id,
                    'video_id': video_id,
                    'title': title,
                    'format': fmt,
                    'type': 'video',
                    'status': ARCHIVED_STATUS,
                    'progress': 100,
                    'speed': '',
                    'eta': '',
                    'created_at': created_at,
                    'filename': path,
                    'file_path': path,
                    'error': None,
                    'is_cache': False,
                    'from_disk': True,
                    'size': size,
                }
                added += 1
            except Exception as e:
                skipped += 1
                print("[Queue] rescan: skipping %r: %s" % (getattr(entry, 'name', '?'), e), flush=True)

        print("[Queue] rescan: %s -> %d archived job(s) restored, %d entr(ies) skipped"
              % (d, added, skipped), flush=True)
        return added

    def add_job(self, video_id, title, fmt, dtype='video', is_cache=False):
        # 1. Deduplication: Check if an active job already exists for this video
        # We allow reusing a 'download' job for a 'cache' request (since it saves the file anyway)
        # We allow reusing a 'cache' job for a 'cache' request.
        # But if 'cache' job exists and we want 'download' (persistent), we should Copy it (handled below), 
        # or if it's currently downloading, we might need a distinct job or wait? 
        # For simplicity: If ANY job exists, return it. Frontend might get a cache path instead of download path, 
        # but for playback it works. For "saving", user might find it in cache folder? 
        # Improve: If is_cache=False (Formal Download) but existing job is_cache=True, we should NOT return it?
        # Because we want the file in Downloads folder.
        
        for jid, job in self.jobs.items():
            if job.get('video_id') == video_id and job.get('status') not in ['error', 'cancelled']:
                existing_is_cache = job.get('is_cache', False)
                # If requests match intent, OR if we strictly want cache and any is available
                if is_cache: 
                    return jid # Any existing job works for cache viewing
                else: 
                     if not existing_is_cache:
                         return jid # Existing download job works for download
                     # If existing is cache, but we want download: Don't return it. Proceed to copy/download logic.

        job_id = str(uuid.uuid4())
        ext = 'mp3' if fmt == 'mp3' else 'mp4'
        video_filename = f"{video_id}.{ext}"
        
        target_dir = self.cache_dir if is_cache else self.download_dir
        target_path = os.path.join(target_dir, video_filename)
        
        print(f"[Queue] Request: {video_id}, is_cache={is_cache}, Target: {target_path}", flush=True)

        # 2. Check Target Existence
        if os.path.exists(target_path):
            if is_cache:
                # Touch file to refresh LRU timestamp
                try: os.utime(target_path, None)
                except: pass
            
            self._create_completed_job(job_id, video_id, title, fmt, dtype, target_path, is_cache)
            return job_id

        # 3. Check Cross-Source (If downloading, check cache. If caching, check download?)
        # If we want explicit download, copying from cache is good.
        # If we want cache, copying from download is also good (save bandwidth).
        
        other_dir = self.download_dir if is_cache else self.cache_dir
        other_path = os.path.join(other_dir, video_filename)
        
        if os.path.exists(other_path):
            try:
                print(f"[Queue] Cache Hit! Copying from {other_path} to {target_path}", flush=True)
                shutil.copy2(other_path, target_path)
                self._create_completed_job(job_id, video_id, title, fmt, dtype, target_path, is_cache)
                return job_id
            except Exception as e:
                print(f"[Queue] Copy failed: {e}", flush=True)

        # 4. Create New Download Job
        job = {
            'job_id': job_id,
            'video_id': video_id,
            'title': title,
            'format': fmt,
            'type': dtype,
            'status': 'queued',
            'progress': 0,
            'speed': '',
            'eta': '',
            'created_at': time.time(),
            'filename': None,
            'file_path': None,
            'error': None,
            'is_cache': is_cache
        }
        self.jobs[job_id] = job
        self.queue.put_nowait(job_id)
        return job_id

    def _create_completed_job(self, job_id, video_id, title, fmt, dtype, path, is_cache):
        self.jobs[job_id] = {
            'job_id': job_id,
            'video_id': video_id,
            'title': title, 
            'format': fmt,
            'type': dtype,
            'status': 'completed',
            'progress': 100,
            'speed': 'Cached',
            'eta': '',
            'created_at': time.time(),
            'filename': path,
            'file_path': path,
            'error': None,
            'is_cache': is_cache
        }

    def get_jobs(self):
        # Return list sorted by created_at desc
        return sorted(self.jobs.values(), key=lambda x: x['created_at'], reverse=True)

    def cancel_job(self, job_id):
        if job_id in self.jobs:
            self.jobs[job_id]['status'] = 'cancelled'

    def clear_job(self, job_id, purge=False):
        """Remove a job from the list. Delete the file from disk ONLY if purge=True.

        The two used to be one action, so a caller that merely wanted to tidy the
        list destroyed the download as a side effect. Removing a job from an
        in-memory dict is cheap and reversible; os.remove is neither. They are now
        separate decisions and the caller has to ask for the destructive one.

        Returns a dict rather than None so "there was no such job" and "the job was
        removed" stop sharing one output -- previously both were silent and the
        endpoint answered 200 {"status": "deleted"} either way, which made a
        duplicate delete indistinguishable from a real one in the log.
        """
        if job_id not in self.jobs:
            return {'removed': False, 'purged': False, 'file': None, 'error': None}

        job = self.jobs[job_id]
        fpath = job.get('file_path') or job.get('filename')
        purged = False
        error = None

        if purge and fpath and os.path.exists(fpath):
            try:
                os.remove(fpath)
                purged = True
            except Exception as e:
                error = str(e)
                print(f"Error deleting file {fpath}: {e}", flush=True)

        del self.jobs[job_id]
        return {'removed': True, 'purged': purged, 'file': fpath, 'error': error}

    async def _worker(self):
        while True:
            job_id = await self.queue.get()
            job = self.jobs[job_id]
            
            if job['status'] == 'cancelled':
                self.queue.task_done()
                continue
                
            self.jobs[job_id]['status'] = 'downloading'
            
            is_cache = job.get('is_cache', False)
            target_dir = self.cache_dir if is_cache else self.download_dir
            
            try:
                success, error = await self.downloader.download(
                    job['video_id'],
                    job['format'],
                    job_id,
                    self._progress_hook,
                    output_dir=target_dir
                )
                
                if success:
                    self.jobs[job_id]['status'] = 'completed'
                    self.jobs[job_id]['progress'] = 100
                    
                    # Set final file path explicitly by finding the actual file
                    # yt-dlp might output .webm or .mkv if ffmpeg is missing or merge failed
                    if job['format'] == 'mp3':
                        final_path = os.path.join(target_dir, f"{job['video_id']}.mp3")
                    else:
                        # Search for video file
                        final_path = None
                        for f in os.listdir(target_dir):
                            if f.startswith(job['video_id'] + '.'):
                                final_path = os.path.join(target_dir, f)
                                break
                        if not final_path:
                            # Fallback assume mp4
                            final_path = os.path.join(target_dir, f"{job['video_id']}.mp4")

                    self.jobs[job_id]['file_path'] = final_path
                    self.jobs[job_id]['filename'] = final_path
                    
                    if is_cache:
                        self._enforce_cache_limit()
                    
                else:
                    self.jobs[job_id]['status'] = 'error'
                    self.jobs[job_id]['error'] = error

            except Exception as e:
                self.jobs[job_id]['status'] = 'error'
                self.jobs[job_id]['error'] = str(e)
            
            self.queue.task_done()

    def _progress_hook(self, job_id, d):
        if job_id not in self.jobs: return
        
        if d['status'] == 'downloading':
            p = d.get('_percent_str', '0%').replace('%','')
            try:
                self.jobs[job_id]['progress'] = float(p)
            except:
                pass
            self.jobs[job_id]['speed'] = d.get('_speed_str', '')
            self.jobs[job_id]['eta'] = d.get('_eta_str', '')
            # d['filename'] might be temp path
            
        elif d['status'] == 'finished':
            self.jobs[job_id]['status'] = 'converting'
            self.jobs[job_id]['progress'] = 99

    def _enforce_cache_limit(self, limit_mb=100):
        try:
            files = []
            total_size = 0
            
            for f in os.listdir(self.cache_dir):
                fp = os.path.join(self.cache_dir, f)
                if os.path.isfile(fp):
                    stat = os.stat(fp)
                    total_size += stat.st_size
                    files.append((fp, stat.st_ctime, stat.st_size)) # Use ctime or mtime? utime updates mtime/atime.
                    # Linux ctime is change time. mtime is modification.
                    # We updated mtime in add_job using utime.
                    
            # Use mtime for LRU
            files.sort(key=lambda x: os.path.getmtime(x[0])) # Oldest mtime first
            
            limit_bytes = limit_mb * 1024 * 1024
            
            if total_size > limit_bytes:
                print(f"[Cache] Size {total_size/1024/1024:.2f}MB > {limit_mb}MB. Cleaning up...", flush=True)
                for fp, _, size in files:
                    if total_size <= limit_bytes:
                        break
                    try:
                        os.remove(fp)
                        total_size -= size
                        print(f"[Cache] Deleted {fp}", flush=True)
                    except Exception as e:
                        print(f"[Cache] Delete error: {e}")
                        
        except Exception as e:
            print(f"[Cache] Enforce limit error: {e}")
