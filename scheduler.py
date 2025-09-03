import logging
import requests
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
import json
import re
from urllib.parse import urlparse, parse_qs

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
    
    def _handle_infinityfree_protection(self, url, session, headers):
        """Handle InfinityFree's anti-bot protection system"""
        try:
            # Make first request to get the protection page
            response = session.get(url, headers=headers, timeout=30)
            
            # Check if we got the anti-bot protection page
            if 'aes.js' in response.text and '__test=' in response.text:
                self.logger.info("Detected InfinityFree anti-bot protection, attempting to bypass...")
                
                # Extract the redirect URL from the JavaScript
                redirect_match = re.search(r'location\.href="([^"]+)"', response.text)
                if redirect_match:
                    redirect_url = redirect_match.group(1)
                    
                    # The JavaScript sets a cookie, but we can try without it first
                    # since the redirect URL contains the bypass parameter
                    self.logger.info(f"Following redirect to: {redirect_url}")
                    
                    # Update headers to look more like a browser
                    browser_headers = headers.copy()
                    browser_headers.update({
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Accept-Encoding': 'gzip, deflate',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                    })
                    
                    # Make the second request to the bypass URL
                    final_response = session.get(redirect_url, headers=browser_headers, timeout=30)
                    return final_response
                else:
                    self.logger.warning("Could not extract redirect URL from protection page")
            
            # If no protection detected, return original response
            return response
            
        except Exception as e:
            self.logger.error(f"Error handling InfinityFree protection: {e}")
            raise
    
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
            
            # Set browser-like headers to avoid anti-bot detection
            if 'User-Agent' not in headers:
                headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            
            # Use session to handle cookies and redirects
            session = requests.Session()
            
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
            
            # Make the request, handling potential anti-bot protection
            if method.upper() == 'GET':
                # For GET requests, use our protection handler
                response = self._handle_infinityfree_protection(url, session, headers)
            else:
                # For other methods, make direct request
                response = session.request(method, url, **request_kwargs)
            
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
