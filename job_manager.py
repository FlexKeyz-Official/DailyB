import json
import os
import uuid
from datetime import datetime
import logging

class JobManager:
    def __init__(self, jobs_file='data/jobs.json', history_file='data/job_history.json'):
        self.jobs_file = jobs_file
        self.history_file = history_file
        self.logger = logging.getLogger(__name__)
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(jobs_file), exist_ok=True)
        
        # Initialize files if they don't exist
        self._init_files()
    
    def _init_files(self):
        """Initialize JSON files if they don't exist"""
        if not os.path.exists(self.jobs_file):
            with open(self.jobs_file, 'w') as f:
                json.dump([], f)
        
        if not os.path.exists(self.history_file):
            with open(self.history_file, 'w') as f:
                json.dump([], f)
    
    def _load_jobs(self):
        """Load jobs from JSON file"""
        try:
            with open(self.jobs_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load jobs: {e}")
            return []
    
    def _save_jobs(self, jobs):
        """Save jobs to JSON file"""
        try:
            with open(self.jobs_file, 'w') as f:
                json.dump(jobs, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save jobs: {e}")
    
    def _load_history(self):
        """Load job execution history from JSON file"""
        try:
            with open(self.history_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load history: {e}")
            return []
    
    def _save_history(self, history):
        """Save job execution history to JSON file"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save history: {e}")
    
    def add_job(self, name, url, cron_expression, method='GET', headers=None, payload=None):
        """Add a new job"""
        jobs = self._load_jobs()
        
        job = {
            'id': str(uuid.uuid4()),
            'name': name,
            'url': url,
            'cron_expression': cron_expression,
            'method': method,
            'headers': headers or {},
            'payload': payload,
            'active': True,
            'created_at': datetime.now().isoformat(),
            'last_run': None,
            'last_status': None
        }
        
        jobs.append(job)
        self._save_jobs(jobs)
        
        self.logger.info(f"Added new job: {name} ({job['id']})")
        return job['id']
    
    def get_all_jobs(self):
        """Get all jobs"""
        return self._load_jobs()
    
    def get_job(self, job_id):
        """Get a specific job by ID"""
        jobs = self._load_jobs()
        for job in jobs:
            if job['id'] == job_id:
                return job
        return None
    
    def delete_job(self, job_id):
        """Delete a job"""
        jobs = self._load_jobs()
        jobs = [job for job in jobs if job['id'] != job_id]
        self._save_jobs(jobs)
        self.logger.info(f"Deleted job: {job_id}")
    
    def update_job_status(self, job_id, active):
        """Update job active status"""
        jobs = self._load_jobs()
        for job in jobs:
            if job['id'] == job_id:
                job['active'] = active
                break
        self._save_jobs(jobs)
        self.logger.info(f"Updated job {job_id} active status to {active}")
    
    def update_job_last_run(self, job_id, status_code, success):
        """Update job last run information"""
        jobs = self._load_jobs()
        for job in jobs:
            if job['id'] == job_id:
                job['last_run'] = datetime.now().isoformat()
                job['last_status'] = 'success' if success else 'failed'
                break
        self._save_jobs(jobs)
    
    def add_execution_history(self, job_id, status_code, execution_time, success, error_message=None, response_content=None):
        """Add an execution record to history"""
        history = self._load_history()
        
        # Update job last run info
        self.update_job_last_run(job_id, status_code, success)
        
        record = {
            'id': str(uuid.uuid4()),
            'job_id': job_id,
            'timestamp': datetime.now().isoformat(),
            'status_code': status_code,
            'execution_time': round(execution_time, 3),
            'success': success,
            'error_message': error_message,
            'response_content': response_content[:1000] if response_content else None  # Limit to 1000 chars
        }
        
        history.append(record)
        
        # Keep only the last 1000 records to prevent file from growing too large
        if len(history) > 1000:
            history = history[-1000:]
        
        self._save_history(history)
        self.logger.debug(f"Added execution history for job {job_id}")
    
    def get_job_history(self, limit=100):
        """Get job execution history"""
        history = self._load_history()
        # Return most recent entries first
        history.reverse()
        return history[:limit]
    
    def clear_history(self):
        """Clear all execution history"""
        self._save_history([])
        self.logger.info("Cleared job execution history")
    
    def get_job_stats(self, job_id):
        """Get statistics for a specific job"""
        history = self._load_history()
        job_history = [record for record in history if record['job_id'] == job_id]
        
        if not job_history:
            return {
                'total_executions': 0,
                'successful_executions': 0,
                'failed_executions': 0,
                'success_rate': 0,
                'average_execution_time': 0
            }
        
        successful = len([r for r in job_history if r['success']])
        total = len(job_history)
        avg_time = sum(r['execution_time'] for r in job_history) / total
        
        return {
            'total_executions': total,
            'successful_executions': successful,
            'failed_executions': total - successful,
            'success_rate': round((successful / total) * 100, 1),
            'average_execution_time': round(avg_time, 3)
        }
