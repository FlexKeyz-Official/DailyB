import os
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from scheduler import CronScheduler
from job_manager import JobManager

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

# Initialize job manager and scheduler
job_manager = JobManager()
scheduler = CronScheduler(job_manager)

# Template filter for date formatting
@app.template_filter('format_datetime')
def format_datetime(date_string, format='%b %d, %H:%M'):
    """Format datetime string for display"""
    try:
        if isinstance(date_string, str):
            dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        else:
            dt = date_string
        return dt.strftime(format)
    except:
        return date_string

@app.route('/')
def index():
    """Display the main dashboard with all jobs"""
    jobs = job_manager.get_all_jobs()
    running_jobs = scheduler.get_running_jobs()
    
    # Add running status to jobs
    for job in jobs:
        job['is_running'] = job['id'] in running_jobs
    
    return render_template('index.html', jobs=jobs)

@app.route('/add_job', methods=['GET', 'POST'])
def add_job():
    """Add a new cron job"""
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            url = request.form.get('url', '').strip()
            cron_expression = request.form.get('cron_expression', '').strip()
            method = request.form.get('method', 'GET')
            headers = request.form.get('headers', '')
            payload = request.form.get('payload', '')
            
            # Validate inputs
            if not name or not url or not cron_expression:
                flash('Name, URL, and cron expression are required', 'error')
                return render_template('add_job.html')
            
            # Validate URL
            if not (url.startswith('http://') or url.startswith('https://')):
                flash('URL must start with http:// or https://', 'error')
                return render_template('add_job.html')
            
            # Parse headers if provided
            parsed_headers = {}
            if headers:
                try:
                    for line in headers.split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            parsed_headers[key.strip()] = value.strip()
                except Exception:
                    flash('Invalid headers format. Use "Key: Value" format, one per line', 'error')
                    return render_template('add_job.html')
            
            # Create job
            job_id = job_manager.add_job(
                name=name,
                url=url,
                cron_expression=cron_expression,
                method=method,
                headers=parsed_headers,
                payload=payload if payload else None
            )
            
            # Schedule the job
            if scheduler.schedule_job(job_id):
                flash(f'Job "{name}" added and scheduled successfully', 'success')
            else:
                flash(f'Job "{name}" added but failed to schedule. Check cron expression.', 'warning')
            
            return redirect(url_for('index'))
            
        except Exception as e:
            flash(f'Error adding job: {str(e)}', 'error')
            logging.error(f"Error adding job: {e}")
    
    return render_template('add_job.html')

@app.route('/delete_job/<job_id>')
def delete_job(job_id):
    """Delete a job"""
    try:
        job = job_manager.get_job(job_id)
        if job:
            # Remove from scheduler
            scheduler.remove_job(job_id)
            # Delete from job manager
            job_manager.delete_job(job_id)
            flash(f'Job "{job["name"]}" deleted successfully', 'success')
        else:
            flash('Job not found', 'error')
    except Exception as e:
        flash(f'Error deleting job: {str(e)}', 'error')
        logging.error(f"Error deleting job {job_id}: {e}")
    
    return redirect(url_for('index'))

@app.route('/toggle_job/<job_id>')
def toggle_job(job_id):
    """Toggle job active status"""
    try:
        job = job_manager.get_job(job_id)
        if job:
            new_status = not job.get('active', True)
            job_manager.update_job_status(job_id, new_status)
            
            if new_status:
                if scheduler.schedule_job(job_id):
                    flash(f'Job "{job["name"]}" activated', 'success')
                else:
                    flash(f'Job "{job["name"]}" activated but scheduling failed', 'warning')
            else:
                scheduler.remove_job(job_id)
                flash(f'Job "{job["name"]}" deactivated', 'info')
        else:
            flash('Job not found', 'error')
    except Exception as e:
        flash(f'Error toggling job: {str(e)}', 'error')
        logging.error(f"Error toggling job {job_id}: {e}")
    
    return redirect(url_for('index'))

@app.route('/run_job/<job_id>')
def run_job_now(job_id):
    """Run a job immediately"""
    try:
        result = scheduler.run_job_now(job_id)
        if result:
            flash('Job executed successfully', 'success')
        else:
            flash('Job execution failed. Check logs for details.', 'error')
    except Exception as e:
        flash(f'Error running job: {str(e)}', 'error')
        logging.error(f"Error running job {job_id}: {e}")
    
    return redirect(url_for('index'))

@app.route('/job_history')
def job_history():
    """Display job execution history"""
    history = job_manager.get_job_history()
    jobs = job_manager.get_all_jobs()
    
    # Create job lookup for names
    job_lookup = {job['id']: job['name'] for job in jobs}
    
    # Add job names to history
    for entry in history:
        entry['job_name'] = job_lookup.get(entry['job_id'], 'Unknown Job')
    
    return render_template('job_history.html', history=history)

@app.route('/clear_history')
def clear_history():
    """Clear job execution history"""
    try:
        job_manager.clear_history()
        flash('Job history cleared successfully', 'success')
    except Exception as e:
        flash(f'Error clearing history: {str(e)}', 'error')
        logging.error(f"Error clearing history: {e}")
    
    return redirect(url_for('job_history'))

if __name__ == '__main__':
    # Start the scheduler
    scheduler.start()
    
    # Load and schedule existing jobs
    jobs = job_manager.get_all_jobs()
    for job in jobs:
        if job.get('active', True):
            scheduler.schedule_job(job['id'])
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
    finally:
        scheduler.shutdown()
