import logging
import requests
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
import json
import re
from urllib.parse import urlparse, parse_qs
import time
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import binascii

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
    
    def _hex_to_bytes(self, hex_string):
        """Convert hex string to bytes"""
        try:
            return bytes.fromhex(hex_string)
        except ValueError:
            return None

    def _decrypt_aes(self, encrypted_hex, key_hex, iv_hex):
        """Decrypt AES encrypted data"""
        try:
            # Convert hex strings to bytes
            encrypted_data = self._hex_to_bytes(encrypted_hex)
            key = self._hex_to_bytes(key_hex)
            iv = self._hex_to_bytes(iv_hex)
            
            if not all([encrypted_data, key, iv]):
                return None
                
            # Create AES cipher in CBC mode
            cipher = AES.new(key, AES.MODE_CBC, iv)
            
            # Decrypt and remove padding
            decrypted = cipher.decrypt(encrypted_data)
            decrypted = unpad(decrypted, AES.block_size)
            
            return decrypted.decode('utf-8')
            
        except Exception as e:
            self.logger.error(f"AES decryption failed: {e}")
            return None

    def _extract_and_set_cookie(self, response_text, session):
        """Extract cookie values from JavaScript and set them in session"""
        try:
            # Try to find the simple cookie pattern first
            simple_cookie_match = re.search(r'document\.cookie="([^"]+)"', response_text)
            if simple_cookie_match:
                cookie_string = simple_cookie_match.group(1)
                # Parse cookie name and value
                if '=' in cookie_string:
                    name, value = cookie_string.split('=', 1)
                    # Remove any additional attributes (path, expires, etc.)
                    value = value.split(';')[0]
                    session.cookies.set(name, value, domain='.dailybred.ct.ws')
                    self.logger.info(f"Set simple cookie: {name}={value}")
                    return True
            
            # Try to extract AES encrypted values - more comprehensive approach
            hex_patterns = re.findall(r'toNumbers\("([a-f0-9]+)"\)', response_text)
            if len(hex_patterns) >= 3:
                self.logger.info(f"Found {len(hex_patterns)} hex patterns for AES decryption")
                
                # Try different combinations of the hex values as key, IV, and encrypted data
                for i in range(len(hex_patterns)):
                    for j in range(len(hex_patterns)):
                        for k in range(len(hex_patterns)):
                            if i != j and j != k and i != k:
                                try:
                                    decrypted = self._decrypt_aes(hex_patterns[i], hex_patterns[j], hex_patterns[k])
                                    if decrypted:
                                        self.logger.info(f"Successfully decrypted AES value: {decrypted}")
                                        session.cookies.set('__test', decrypted, domain='.dailybred.ct.ws')
                                        session.cookies.set('__test', decrypted, domain='dailybred.ct.ws')
                                        return True
                                except:
                                    continue
            
            # Try to find direct cookie assignments in JavaScript
            js_cookie_patterns = [
                r'document\.cookie\s*=\s*["\']([^"\']+)["\']',
                r'cookie\s*=\s*["\']([^"\']+)["\']',
                r'__test["\']?\s*=\s*["\']([^"\']+)["\']'
            ]
            
            for pattern in js_cookie_patterns:
                matches = re.findall(pattern, response_text, re.IGNORECASE)
                for match in matches:
                    if '=' in match:
                        name, value = match.split('=', 1)
                        session.cookies.set(name.strip(), value.split(';')[0].strip(), domain='.dailybred.ct.ws')
                        self.logger.info(f"Set JS extracted cookie: {name.strip()}={value.split(';')[0].strip()}")
                        return True
            
            # As a last resort, try to generate a plausible cookie value
            if hex_patterns:
                # Use the first hex pattern as a potential cookie value
                test_value = hex_patterns[0][:32]  # Take first 32 chars as cookie value
                session.cookies.set('__test', test_value, domain='.dailybred.ct.ws')
                session.cookies.set('__test', test_value, domain='dailybred.ct.ws')
                self.logger.info(f"Set fallback hex cookie: __test={test_value}")
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error extracting cookie: {e}")
            return False

    def _handle_infinityfree_protection(self, url, session, headers):
        """Handle InfinityFree's multi-step anti-bot protection system with proper cookie handling"""
        try:
            # Update headers to look more like a browser
            browser_headers = headers.copy()
            browser_headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
            })
            
            current_url = url
            max_redirects = 10  # Prevent infinite loops
            redirect_count = 0
            response = None  # Initialize response variable
            
            while redirect_count < max_redirects:
                # Make request to current URL
                response = session.get(current_url, headers=browser_headers, timeout=30)
                
                # Check if we got the anti-bot protection page
                if 'aes.js' in response.text and '__test=' in response.text:
                    self.logger.info(f"Detected InfinityFree anti-bot protection (step {redirect_count + 1}), attempting to bypass...")
                    
                    # Try to extract and set cookies from the JavaScript
                    self._extract_and_set_cookie(response.text, session)
                    
                    # Extract the redirect URL from the JavaScript
                    redirect_match = re.search(r'location\.href="([^"]+)"', response.text)
                    if redirect_match:
                        current_url = redirect_match.group(1)
                        self.logger.info(f"Following redirect to: {current_url}")
                        redirect_count += 1
                        
                        # Small delay to mimic browser behavior
                        time.sleep(1.0)  # Increased delay
                        continue
                    else:
                        self.logger.warning("Could not extract redirect URL from protection page")
                        break
                        
                # Check for cookies not enabled page
                elif 'Cookies are not enabled' in response.text:
                    self.logger.warning("Hit cookies not enabled page - protection bypass incomplete")
                    # Try one more time with different approach
                    if redirect_count == 0:
                        # Set a basic cookie and try again
                        session.cookies.set('__test', 'test_value', domain='.dailybred.ct.ws')
                        session.cookies.set('__test', 'test_value', domain='dailybred.ct.ws')
                        self.logger.info("Set basic test cookies and retrying...")
                        redirect_count += 1
                        time.sleep(1.0)
                        continue
                    else:
                        break
                else:
                    # No more protection pages, return the final response
                    if redirect_count > 0:
                        self.logger.info(f"Successfully bypassed InfinityFree protection after {redirect_count} redirects")
                    return response
            
            # If we hit max redirects, return the last response
            if redirect_count >= max_redirects:
                self.logger.warning(f"Hit maximum redirect limit ({max_redirects}), returning last response")
            
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
