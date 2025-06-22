# Django Task Management System - Installation Guide

## Table of Contents
1. [System Requirements](#system-requirements)
2. [Installation Steps](#installation-steps)
3. [Configuration](#configuration)
4. [Initial Setup](#initial-setup)
5. [Running the Application](#running-the-application)
6. [Production Deployment](#production-deployment)
7. [Maintenance](#maintenance)
8. [Troubleshooting](#troubleshooting)

## System Requirements

### Minimum Requirements
- **Operating System**: Windows 10, macOS 10.14, or Linux (Ubuntu 18.04+)
- **Python**: Version 3.8 or higher
- **RAM**: 2GB minimum, 4GB recommended
- **Storage**: 1GB free space
- **Browser**: Chrome 90+, Firefox 88+, Safari 14+, or Edge 90+

### Recommended Requirements
- **Python**: Version 3.11 or higher
- **RAM**: 8GB or more
- **Storage**: 5GB free space for logs and data
- **Database**: PostgreSQL for production use

## Installation Steps

### Step 1: Download and Extract

1. Download the project zip file
2. Extract to your desired location (e.g., `C:\TaskManager` or `/opt/taskmanager`)
3. Open a terminal/command prompt in the extracted directory

### Step 2: Python Environment Setup

#### Option A: Using Virtual Environment (Recommended)
```bash
# Create virtual environment
python -m venv task_manager_env

# Activate virtual environment
# On Windows:
task_manager_env\Scripts\activate
# On macOS/Linux:
source task_manager_env/bin/activate
```

#### Option B: Using System Python
Skip this step if you prefer to use system Python (not recommended for production)

### Step 3: Install Dependencies

```bash
# Install required Python packages
pip install django==5.2.3
pip install djangorestframework
pip install django-cors-headers
pip install openpyxl
pip install xlsxwriter
pip install python-dateutil
```

Or install from requirements file if provided:
```bash
pip install -r requirements.txt
```

### Step 4: Database Setup

```bash
# Create database tables
python manage.py makemigrations
python manage.py migrate
```

### Step 5: Create Sample Data (Optional)

```bash
# Create sample users and divisions
python manage.py create_sample_data
```

This creates:
- Admin user (username: admin, password: admin123)
- 5 sample divisions (Engineering, Finance, HR, Marketing, Sales)
- 5 sample users with different roles
- 6 sample tasks for testing

## Configuration

### Database Configuration

#### SQLite (Default - Development)
No additional configuration needed. The system uses SQLite by default.

#### PostgreSQL (Production)
1. Install PostgreSQL
2. Create a database and user
3. Update `settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'taskmanager',
        'USER': 'your_username',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### Email Configuration (Optional)

For email notifications, update `settings.py`:

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'your-smtp-server.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@domain.com'
EMAIL_HOST_PASSWORD = 'your-email-password'
```

### Security Settings

For production, update these settings in `settings.py`:

```python
# Set to False in production
DEBUG = False

# Add your domain
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']

# Generate a new secret key
SECRET_KEY = 'your-new-secret-key-here'

# Security headers
SECURE_SSL_REDIRECT = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
```

## Initial Setup

### Step 1: Create Superuser

```bash
python manage.py createsuperuser
```

Follow the prompts to create an administrator account.

### Step 2: Create Divisions

1. Start the development server (see next section)
2. Log in with your superuser account
3. Go to Users → Add divisions for your organization
4. Create user accounts and assign them to divisions

### Step 3: Configure System Settings

1. Access the admin interface at `/admin/`
2. Configure any additional settings as needed
3. Set up user permissions and roles

## Running the Application

### Development Server

```bash
# Start the development server
python manage.py runserver

# Or specify host and port
python manage.py runserver 0.0.0.0:8000
```

The application will be available at:
- Local access: http://localhost:8000
- Network access: http://your-ip-address:8000

### Default Login Credentials

If you used the sample data command:
- **Username**: admin
- **Password**: admin123

Additional test users:
- john_doe / password123
- jane_smith / password123
- david_brown / password123
- sarah_jones / password123
- mike_wilson / password123

## Production Deployment

### Using Gunicorn (Recommended)

1. Install Gunicorn:
```bash
pip install gunicorn
```

2. Create a Gunicorn configuration file (`gunicorn.conf.py`):
```python
bind = "0.0.0.0:8000"
workers = 3
worker_class = "sync"
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
```

3. Run with Gunicorn:
```bash
gunicorn --config gunicorn.conf.py task_manager.wsgi:application
```

### Using Apache/Nginx

#### Nginx Configuration Example
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    location /static/ {
        alias /path/to/your/project/static/;
    }
    
    location /media/ {
        alias /path/to/your/project/media/;
    }
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Static Files for Production

```bash
# Collect static files
python manage.py collectstatic
```

## Maintenance

### Regular Tasks

#### Database Backup
```bash
# SQLite backup
cp db.sqlite3 backup_$(date +%Y%m%d).sqlite3

# PostgreSQL backup
pg_dump taskmanager > backup_$(date +%Y%m%d).sql
```

#### Log Rotation
Set up log rotation for Django logs and web server logs.

#### Updates
1. Backup database and files
2. Update code
3. Run migrations: `python manage.py migrate`
4. Collect static files: `python manage.py collectstatic`
5. Restart application server

### Monitoring

#### Health Checks
- Monitor application response time
- Check database connectivity
- Monitor disk space usage
- Track error logs

#### Performance Monitoring
- Database query performance
- Memory usage
- CPU utilization
- User activity patterns

## Troubleshooting

### Common Installation Issues

#### Python Version Error
```
Error: Python 3.8+ required
```
**Solution**: Install Python 3.8 or higher

#### Permission Denied
```
Error: Permission denied when creating files
```
**Solution**: Run with appropriate permissions or change directory ownership

#### Database Connection Error
```
Error: Unable to connect to database
```
**Solution**: 
1. Check database server is running
2. Verify connection settings
3. Ensure database exists
4. Check user permissions

#### Missing Dependencies
```
Error: No module named 'django'
```
**Solution**: Install dependencies with `pip install -r requirements.txt`

### Runtime Issues

#### Static Files Not Loading
1. Run `python manage.py collectstatic`
2. Check `STATIC_URL` and `STATIC_ROOT` settings
3. Verify web server configuration

#### 500 Internal Server Error
1. Check Django logs
2. Verify database connectivity
3. Check file permissions
4. Review settings configuration

#### Slow Performance
1. Enable database query optimization
2. Add database indexes
3. Configure caching
4. Optimize static file serving

### Getting Help

#### Log Files
- Django logs: Check `logs/` directory
- Web server logs: Check server-specific locations
- Database logs: Check database server logs

#### Debug Mode
For development troubleshooting, set `DEBUG = True` in settings.py

#### Support Resources
- Django Documentation: https://docs.djangoproject.com/
- Project Repository: [Your repository URL]
- Issue Tracker: [Your issue tracker URL]

---

## Quick Start Checklist

- [ ] Python 3.8+ installed
- [ ] Virtual environment created and activated
- [ ] Dependencies installed
- [ ] Database migrations run
- [ ] Superuser created
- [ ] Sample data loaded (optional)
- [ ] Development server started
- [ ] Application accessible in browser
- [ ] Login successful

**Congratulations!** Your Django Task Management System is now ready to use.

**Version**: 1.0  
**Last Updated**: June 2025  
**Installation Guide**: Complete Setup Instructions

