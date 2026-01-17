
import asyncio
import uuid
import time
from downloader import Downloader

class QueueManager:
    def __init__(self, download_dir):
        self.downloader = Downloader(download_dir)
        self.jobs = {} # { job_id: { ... } }
        self.queue = asyncio.Queue()
        self.active_workers = 0
        self.max_workers = 1 # Limit to 1 concurrent download for low spec
        
        # Start worker
        asyncio.create_task(self._worker())

    def add_job(self, video_id, title, fmt, dtype='video'):
        job_id = str(uuid.uuid4())
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
            'error': None
        }
        self.jobs[job_id] = job
        self.queue.put_nowait(job_id)
        return job_id

    def get_jobs(self):
        # Return list sorted by created_at desc
        return sorted(self.jobs.values(), key=lambda x: x['created_at'], reverse=True)

    def cancel_job(self, job_id):
        if job_id in self.jobs:
            self.jobs[job_id]['status'] = 'cancelled'
            # Note: Killing a running thread/process is hard with simple run_in_executor
            # This mainly stops queued jobs or updates status. 
            # Real cancellation requires more complex process management.

    def clear_job(self, job_id):
        if job_id in self.jobs:
            # Try to delete file
            job = self.jobs[job_id]
            fpath = job.get('file_path') or job.get('filename')
            if fpath:
                import os
                try:
                    if os.path.exists(fpath):
                        os.remove(fpath)
                except Exception as e:
                    print(f"Error deleting file {fpath}: {e}")
            
            del self.jobs[job_id]

    async def _worker(self):
        while True:
            job_id = await self.queue.get()
            if self.jobs[job_id]['status'] == 'cancelled':
                self.queue.task_done()
                continue
                
            self.jobs[job_id]['status'] = 'downloading'
            
            try:
                success, error = await self.downloader.download(
                    self.jobs[job_id]['video_id'],
                    self.jobs[job_id]['format'],
                    job_id,
                    self._progress_hook
                )
                
                if success:
                    self.jobs[job_id]['status'] = 'completed'
                    self.jobs[job_id]['progress'] = 100
                    
                    # Set final file path explicitly
                    ext = 'mp3' if self.jobs[job_id]['format'] == 'mp3' else 'mp4'
                    # Ensure path matches what downloader produced
                    final_path = f"{self.downloader.download_dir}/{job_id}.{ext}"
                    self.jobs[job_id]['file_path'] = final_path
                    self.jobs[job_id]['filename'] = final_path
                    
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
            # d has _percent_str, _eta_str, etc.
            p = d.get('_percent_str', '0%').replace('%','')
            try:
                self.jobs[job_id]['progress'] = float(p)
            except:
                pass
            self.jobs[job_id]['speed'] = d.get('_speed_str', '')
            self.jobs[job_id]['eta'] = d.get('_eta_str', '')
            self.jobs[job_id]['filename'] = d.get('filename', '')
            
        elif d['status'] == 'finished':
            self.jobs[job_id]['status'] = 'converting' # FFMpeg post-processing usually handles here
            self.jobs[job_id]['progress'] = 99
