# Overview

This is a web-based Cron Job Manager built with Flask that allows users to create, schedule, and monitor HTTP-based cron jobs. The application provides a user-friendly interface for managing scheduled tasks that make HTTP requests to specified URLs at defined intervals using cron expressions.

The system enables users to:
- Create and configure cron jobs with custom HTTP requests
- Schedule jobs using standard cron syntax
- Monitor job execution history and status
- Start, stop, and manage running jobs through a web dashboard

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Technology**: Server-side rendered HTML templates using Jinja2
- **Styling**: Bootstrap 5 with dark theme and Bootstrap Icons for UI components
- **Structure**: Template inheritance with a base layout and specialized pages for different functions
- **Client-side**: Basic JavaScript for form validation, tooltips, and dashboard auto-refresh functionality

## Backend Architecture
- **Framework**: Flask web framework with Blueprint-style routing
- **Architecture Pattern**: Modular design with separated concerns:
  - `app.py` - Main Flask application and route handlers
  - `job_manager.py` - Data persistence and job CRUD operations
  - `scheduler.py` - Background job scheduling using APScheduler
- **Job Execution**: Background thread pool executor for concurrent job execution
- **Request Handling**: Uses Python requests library for HTTP calls to job endpoints

## Data Storage Solutions
- **Primary Storage**: JSON file-based persistence for simplicity and portability
- **Data Files**:
  - `data/jobs.json` - Stores job configurations and metadata
  - `data/job_history.json` - Maintains execution history and logs
- **Design Decision**: Chose file-based storage over database for lightweight deployment and minimal dependencies

## Scheduling System
- **Scheduler**: APScheduler (Advanced Python Scheduler) with BackgroundScheduler
- **Trigger Type**: CronTrigger for standard cron expression support
- **Concurrency**: ThreadPoolExecutor with configurable pool size (default: 20 threads)
- **Job Management**: Dynamic job addition/removal with conflict resolution

## Application Structure
- **Static Assets**: CSS and JavaScript files served from `/static` directory
- **Templates**: HTML templates in `/templates` with inheritance hierarchy
- **Configuration**: Environment-based configuration with sensible defaults
- **Logging**: Python logging module for debugging and monitoring

# External Dependencies

## Core Libraries
- **Flask** - Web framework for HTTP server and routing
- **APScheduler** - Background job scheduling and cron expression parsing
- **Requests** - HTTP client library for making job requests

## Frontend Dependencies
- **Bootstrap 5** - CSS framework with dark theme variant
- **Bootstrap Icons** - Icon library for UI elements
- **Custom CSS/JS** - Application-specific styling and client-side functionality

## Development Dependencies
- **Jinja2** - Template engine (included with Flask)
- **Python Standard Library** - JSON, logging, datetime, UUID, and OS modules

## External Service Integration
- **HTTP Endpoints** - The application makes outbound HTTP requests to user-configured URLs
- **No Database Required** - Uses local file system for data persistence
- **Environment Variables** - SESSION_SECRET for Flask session management