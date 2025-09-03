import logging
import requests
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
import json

class CronScheduler:
    def __init__(self, job_manager):
        self.job_manager = job_manager
        self.scheduler = BackgroundScheduler(
            executors={'default': ThreadPoolExecutor(20)},
            job_defaults={'coalesce': False, 'max_instances': 3}
        )
        self.logger = logging.getLogger(__name__)
    
    def start(self):
        """Start the scheduler"""
        try:
            self.scheduler.start()
            self.logger.info("Scheduler started successfully")
        except Exception as e:
            self.logger.error(f"Failed to start scheduler: {e}")
    
    def shutdown(self):
        """Shutdown the scheduler"""
        try:
            self.scheduler.shutdown()
            self.logger.info("Scheduler shutdown successfully")
        except Exception as e:
            self.logger.error(f"Failed to shutdown scheduler: {e}")
    
    def schedule_job(self, job_id):
        """Schedule a job with APScheduler"""
        try:
            job = self.job_manager.get_job(job_id)
            if not job:
                self.logger.error(f"Job {job_id} not found")
                return False
            
            # Remove existing job if it exists
            self.remove_job(job_id)
            
            # Parse cron expression
            cron_parts = job['cron_expression'].split()
            if len(cron_parts) != 5:
                self.logger.error(f"Invalid cron expression for job {job_id}: {job['cron_expression']}")
                return False
            
            minute, hour, day, month, day_of_week = cron_parts
            
            # Create cron trigger
            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week
            )
            
            # Schedule the job
            self.scheduler.add_job(
                func=self._execute_job,
                trigger=trigger,
                id=job_id,
                args=[job_id],
                replace_existing=True
            )
            
            self.logger.info(f"Job {job_id} scheduled with cron expression: {job['cron_expression']}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to schedule job {job_id}: {e}")
            return False
    
    def remove_job(self, job_id):
        """Remove a job from the scheduler"""
        try:
            self.scheduler.remove_job(job_id)
            self.logger.info(f"Job {job_id} removed from scheduler")
        except Exception as e:
            # Job might not exist, which is fine
            pass
    
    def get_running_jobs(self):
        """Get list of currently scheduled job IDs"""
        try:
            return [job.id for job in self.scheduler.get_jobs()]
        except Exception as e:
            self.logger.error(f"Failed to get running jobs: {e}")
            return []
    
    def run_job_now(self, job_id):
        """Execute a job immediately"""
        try:
            return self._execute_job(job_id)
        except Exception as e:
            self.logger.error(f"Failed to run job {job_id} immediately: {e}")
            return False
    
    def _execute_job(self, job_id):
        """Execute a job by making HTTP request"""
        start_time = datetime.now()
        
        try:
            job = self.job_manager.get_job(job_id)
            if not job:
                self.logger.error(f"Job {job_id} not found during execution")
                return False
            
            self.logger.info(f"Executing job {job_id}: {job['name']}")
            
            # Prepare request parameters
            method = job.get('method', 'GET').upper()
            url = job['url']
            headers = job.get('headers', {})
            payload = job.get('payload')
            
            # Set default headers
            if 'User-Agent' not in headers:
                headers['User-Agent'] = 'CronJobManager/1.0'
            
            # Prepare request kwargs
            request_kwargs = {
                'timeout': 30,
                'headers': headers
            }
            
            # Add payload for POST/PUT/PATCH requests
            if method in ['POST', 'PUT', 'PATCH'] and payload:
                if headers.get('Content-Type', '').startswith('application/json'):
                    request_kwargs['json'] = json.loads(payload)
                else:
                    request_kwargs['data'] = payload
            
            # Make the request
            response = requests.request(method, url, **request_kwargs)
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Log the result
            success = 200 <= response.status_code < 400
            
            if success:
                self.logger.info(f"Job {job_id} executed successfully. Status: {response.status_code}, Time: {execution_time:.2f}s")
            else:
                self.logger.warning(f"Job {job_id} returned status {response.status_code}. Time: {execution_time:.2f}s")
            
            # Record execution history
            self.job_manager.add_execution_history(
                job_id=job_id,
                status_code=response.status_code,
                execution_time=execution_time,
                success=success,
                error_message=None if success else f"HTTP {response.status_code}: {response.text[:200]}",
                response_content=response.text if success else None
            )
            
            return success
            
        except requests.RequestException as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            error_message = f"Request failed: {str(e)}"
            self.logger.error(f"Job {job_id} failed: {error_message}")
            
            # Record failure in history
            self.job_manager.add_execution_history(
                job_id=job_id,
                status_code=None,
                execution_time=execution_time,
                success=False,
                error_message=error_message,
                response_content=None
            )
            
            return False
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            error_message = f"Unexpected error: {str(e)}"
            self.logger.error(f"Job {job_id} failed with unexpected error: {error_message}")
            
            # Record failure in history
            self.job_manager.add_execution_history(
                job_id=job_id,
                status_code=None,
                execution_time=execution_time,
                success=False,
                error_message=error_message,
                response_content=None
            )
            
            return False
