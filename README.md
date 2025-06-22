# Django Task Management System

A comprehensive web application for managing tasks, tracking progress, and generating detailed reports. Built with Django, Bootstrap 5, and modern web technologies.

![Task Management System](https://img.shields.io/badge/Django-5.2.3-green)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3.0-blue)
![Python](https://img.shields.io/badge/Python-3.8+-yellow)

## 🚀 Features

### Core Functionality
- **Task Management**: Create, assign, track, and manage tasks with priorities and deadlines
- **User Management**: Custom user model with division-based organization
- **Commenting System**: Collaborative commenting with admin-only internal comments
- **Status Tracking**: Real-time task status updates with history tracking
- **Role-based Access**: Different permissions for users and administrators

### Advanced Features
- **Comprehensive Reports**: Analytics dashboard with filtering and export capabilities
- **Data Export**: Excel and CSV export functionality
- **Modern UI**: Responsive design with Bootstrap 5 and SweetAlert notifications
- **Search & Filter**: Advanced filtering and search capabilities
- **Activity History**: Complete audit trail for all task changes
- **Dashboard Analytics**: Visual statistics and performance metrics

### Technical Features
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Security**: Built-in Django security features and CSRF protection
- **Database**: SQLite for development, PostgreSQL ready for production
- **API Ready**: Django REST framework integration
- **Scalable**: Designed for multi-user, multi-division organizations

## 📋 Requirements

- Python 3.8 or higher
- Django 5.2.3
- Modern web browser (Chrome 90+, Firefox 88+, Safari 14+, Edge 90+)

## 🛠️ Quick Installation

1. **Extract the project files**
   ```bash
   unzip django_task_manager.zip
   cd django_task_manager
   ```

2. **Create virtual environment**
   ```bash
   python -m venv task_manager_env
   source task_manager_env/bin/activate  # On Windows: task_manager_env\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Setup database**
   ```bash
   python manage.py migrate
   python manage.py create_sample_data
   ```

5. **Run the application**
   ```bash
   python manage.py runserver
   ```

6. **Access the application**
   - Open your browser and go to: http://localhost:8000
   - Login with: **admin** / **admin123**

## 📚 Documentation

- **[Installation Guide](INSTALLATION.md)**: Complete setup instructions
- **[User Guide](USER_GUIDE.md)**: Comprehensive user documentation

## 🎯 Default Login Credentials

### Administrator Account
- **Username**: admin
- **Password**: admin123

### Test User Accounts
- john_doe / password123 (Engineering)
- jane_smith / password123 (Engineering)
- david_brown / password123 (Sales)
- sarah_jones / password123 (Marketing)
- mike_wilson / password123 (Marketing)

## 🏗️ Project Structure

```
django_task_manager/
├── task_manager/          # Django project settings
├── tasks/                 # Main application
│   ├── models.py         # Database models
│   ├── views.py          # Application views
│   ├── forms.py          # Django forms
│   ├── admin.py          # Admin interface
│   └── management/       # Custom management commands
├── templates/            # HTML templates
│   ├── base.html        # Base template
│   ├── registration/    # Authentication templates
│   └── tasks/           # Task-related templates
├── static/              # Static files (CSS, JS, images)
├── media/               # User uploaded files
├── requirements.txt     # Python dependencies
├── manage.py           # Django management script
├── USER_GUIDE.md       # User documentation
├── INSTALLATION.md     # Installation instructions
└── README.md           # This file
```

## 🔧 Key Components

### Models
- **CustomUser**: Extended user model with division and admin roles
- **Division**: Organizational units for grouping users
- **Task**: Core task model with status, priority, and assignment
- **Comment**: Commenting system for collaboration
- **TaskHistory**: Audit trail for all task changes

### Views
- **Dashboard**: Overview with statistics and recent activity
- **Task Management**: CRUD operations for tasks
- **User Management**: Admin interface for user administration
- **Reports**: Analytics and export functionality

### Templates
- **Responsive Design**: Bootstrap 5 with mobile-first approach
- **Interactive UI**: SweetAlert2 for notifications and confirmations
- **Modern Styling**: Clean, professional interface

## 🎨 Screenshots

### Dashboard
- Task statistics with visual cards
- Recent activity timeline
- Quick action buttons

### Task Management
- Comprehensive task list with filtering
- Detailed task view with comments
- Task creation and editing forms

### Reports & Analytics
- Visual charts and statistics
- Advanced filtering options
- Excel and CSV export functionality

## 🔒 Security Features

- Django's built-in security features
- CSRF protection
- User authentication and authorization
- Role-based access control
- Secure password handling
- SQL injection prevention

## 🚀 Production Deployment

### Recommended Stack
- **Web Server**: Nginx or Apache
- **Application Server**: Gunicorn
- **Database**: PostgreSQL
- **Caching**: Redis (optional)
- **Static Files**: CDN or web server

### Environment Variables
```bash
DEBUG=False
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:pass@localhost/dbname
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

## 📈 Performance

- Optimized database queries
- Efficient pagination
- Static file optimization
- Responsive design for all devices
- Minimal JavaScript dependencies

## 🤝 Support

### Getting Help
1. Check the [User Guide](USER_GUIDE.md) for detailed instructions
2. Review the [Installation Guide](INSTALLATION.md) for setup issues
3. Contact your system administrator

### Reporting Issues
When reporting issues, please include:
- Browser and version
- Steps to reproduce
- Error messages
- Screenshots (if applicable)

## 📝 License

This project is proprietary software. All rights reserved.

## 🏷️ Version Information

- **Version**: 1.0
- **Release Date**: June 2025
- **Django Version**: 5.2.3
- **Python Version**: 3.8+
- **Bootstrap Version**: 5.3.0

## 🎉 Features Highlights

### For Users
- ✅ Intuitive task creation and management
- ✅ Real-time status updates
- ✅ Collaborative commenting
- ✅ Personal dashboard with task overview
- ✅ Mobile-friendly interface

### For Administrators
- ✅ Comprehensive user management
- ✅ Advanced reporting and analytics
- ✅ Data export capabilities
- ✅ System-wide task oversight
- ✅ Audit trails and history tracking

### For Organizations
- ✅ Division-based organization
- ✅ Role-based permissions
- ✅ Scalable architecture
- ✅ Professional interface
- ✅ Comprehensive documentation

---

**Ready to get started?** Follow the [Installation Guide](INSTALLATION.md) and begin managing your tasks efficiently!

For detailed usage instructions, see the [User Guide](USER_GUIDE.md).

