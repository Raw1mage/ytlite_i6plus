
import asyncio
import uuid
import time
import os
import shutil
from downloader import Downloader

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
        
        # Start worker
        asyncio.create_task(self._worker())

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
