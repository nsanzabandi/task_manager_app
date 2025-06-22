# Django Task Management System - User Guide

## Table of Contents
1. [Introduction](#introduction)
2. [System Overview](#system-overview)
3. [Getting Started](#getting-started)
4. [User Roles and Permissions](#user-roles-and-permissions)
5. [Dashboard](#dashboard)
6. [Task Management](#task-management)
7. [User Management](#user-management)
8. [Reports and Analytics](#reports-and-analytics)
9. [Advanced Features](#advanced-features)
10. [Troubleshooting](#troubleshooting)

## Introduction

The Django Task Management System is a comprehensive web application designed to help organizations manage tasks, track progress, and generate detailed reports. Built with modern web technologies including Django, Bootstrap 5, and SweetAlert, it provides an intuitive interface for both regular users and administrators.

### Key Features

- **User Management**: Custom user model with division-based organization
- **Task Management**: Create, assign, track, and manage tasks with priorities and deadlines
- **Commenting System**: Collaborative commenting with admin-only internal comments
- **Reporting**: Comprehensive analytics with filtering and export capabilities
- **Modern UI**: Responsive design with Bootstrap 5 and interactive notifications
- **Role-based Access**: Different permissions for users and administrators
- **Export Functionality**: Excel and CSV export for reports and data analysis




## System Overview

### Architecture

The system is built using the Django web framework with the following components:

- **Backend**: Django 5.2.3 with SQLite database
- **Frontend**: Bootstrap 5 with responsive design
- **Notifications**: SweetAlert2 for interactive user feedback
- **Export**: XlsxWriter and CSV modules for data export
- **Authentication**: Django's built-in authentication system with custom user model

### Database Models

1. **CustomUser**: Extended user model with division assignment and admin roles
2. **Division**: Organizational units for grouping users and tasks
3. **Task**: Core task model with all task-related information
4. **Comment**: Comments system for task collaboration
5. **TaskHistory**: Audit trail for task changes

## Getting Started

### First Login

1. Navigate to the application URL in your web browser
2. Use the credentials provided by your administrator
3. If this is your first login, you may be prompted to change your password
4. You'll be redirected to the dashboard upon successful login

### Dashboard Overview

The dashboard provides a quick overview of your tasks and system statistics:

- **Task Statistics**: Visual cards showing total, pending, in-progress, and completed tasks
- **Recent Tasks**: List of recently created or updated tasks
- **My Tasks**: Tasks specifically assigned to you
- **Quick Actions**: Shortcuts to common operations

## User Roles and Permissions

### Regular Users

Regular users can:
- View tasks assigned to them or in their division
- Create new tasks
- Comment on tasks
- Update task status (for assigned tasks)
- View basic reports

### Division Administrators

Division administrators have additional permissions:
- Manage users within their division
- View all tasks in their division
- Assign tasks to users in their division
- Add internal comments visible only to admins
- Access detailed reports for their division

### System Administrators

System administrators have full access:
- Manage all users across all divisions
- View and manage all tasks
- Access comprehensive system reports
- Export data in various formats
- Manage system settings


## Task Management

### Creating a New Task

1. Click on "Create Task" in the sidebar or use the "New Task" button on the dashboard
2. Fill in the required information:
   - **Task Title**: Clear, descriptive title for the task
   - **Description**: Detailed description of what needs to be done
   - **Priority**: Low, Medium, High, or Urgent
   - **Assigned To**: Select the user responsible for the task
   - **Status**: Initial status (usually Pending)
   - **Due Date**: Optional deadline for the task
   - **Estimated Hours**: Optional time estimate

3. Click "Create Task" to save

### Task Statuses

- **Pending**: Task has been created but work hasn't started
- **In Progress**: Task is currently being worked on
- **Completed**: Task has been finished
- **Cancelled**: Task has been cancelled or is no longer needed

### Viewing and Managing Tasks

#### Task List View

The task list provides a comprehensive view of all tasks with:
- Filtering options by status, priority, division, and assigned user
- Search functionality to find specific tasks
- Sortable columns for easy organization
- Pagination for large task lists

#### Task Detail View

Each task has a detailed view showing:
- Complete task information and metadata
- Comment history and collaboration area
- Activity timeline showing all changes
- Quick action buttons for common operations
- Related tasks and dependencies

### Commenting on Tasks

1. Navigate to the task detail page
2. Scroll to the Comments section
3. Type your comment in the text area
4. For administrators: Check "Internal comment" for admin-only visibility
5. Click "Add Comment" to post

### Updating Task Status

1. Open the task detail page
2. Use the "Update Status" button or dropdown
3. Select the new status
4. The change will be logged in the activity history

## User Management

### Viewing Users (Admin Only)

1. Click "Users" in the sidebar
2. View the list of all system users
3. See user details including division, role, and status

### Adding New Users (Admin Only)

1. Go to the Users page
2. Click "Add New User"
3. Fill in user information:
   - Username and email
   - First and last name
   - Division assignment
   - Admin privileges (if applicable)
4. Set initial password
5. Save the user

### Editing User Information (Admin Only)

1. Find the user in the Users list
2. Click "Edit" next to their name
3. Modify the necessary information
4. Save changes

## Reports and Analytics

### Accessing Reports

1. Click "Reports" in the sidebar
2. The reports dashboard will display current statistics and charts

### Available Reports

#### Task Statistics
- Total tasks in the system
- Tasks by status (pending, in progress, completed, overdue)
- Priority distribution
- Division workload distribution

#### Performance Metrics
- Average task completion time
- Task completion rate
- Overdue task count
- Recent activity summary

### Filtering Reports

Use the filter panel to customize reports:
- **Date Range**: Filter by creation or completion date
- **Status**: Show only tasks with specific statuses
- **Priority**: Filter by task priority level
- **Division**: Show tasks from specific divisions
- **Assigned User**: Filter by task assignee

### Exporting Data

#### Excel Export
1. Set your desired filters
2. Click "Export Excel"
3. The file will download automatically with:
   - Task details spreadsheet
   - Summary statistics
   - Charts and visualizations

#### CSV Export
1. Apply filters as needed
2. Click "Export CSV"
3. Download the CSV file for use in other applications


## Advanced Features

### Task History and Audit Trail

Every task maintains a complete history of changes including:
- Status updates
- Assignment changes
- Comment additions
- Metadata modifications
- User who made each change
- Timestamp of each action

### Search and Filtering

#### Global Search
- Use the search box in the task list to find tasks by title or description
- Search is case-insensitive and supports partial matches

#### Advanced Filtering
- Combine multiple filters for precise results
- Save common filter combinations for quick access
- Clear all filters with one click

### Notifications and Alerts

The system uses SweetAlert2 for user-friendly notifications:
- Success messages for completed actions
- Error alerts for failed operations
- Confirmation dialogs for destructive actions
- Progress indicators for long-running operations

### Responsive Design

The application is fully responsive and works on:
- Desktop computers
- Tablets
- Mobile phones
- Various screen sizes and orientations

### Keyboard Shortcuts

- **Ctrl+N**: Create new task (when on task pages)
- **Ctrl+S**: Save current form
- **Esc**: Close modal dialogs
- **Enter**: Submit forms and confirm actions

## Troubleshooting

### Common Issues

#### Cannot Login
1. Verify your username and password
2. Check if your account is active
3. Contact your administrator if the issue persists
4. Clear browser cache and cookies

#### Tasks Not Displaying
1. Check your filter settings
2. Verify you have permission to view the tasks
3. Refresh the page
4. Contact support if tasks are missing

#### Export Not Working
1. Ensure you have the necessary permissions
2. Check if filters are too restrictive (no results)
3. Try a different browser
4. Contact administrator for server issues

#### Slow Performance
1. Clear browser cache
2. Check internet connection
3. Reduce the number of tasks displayed per page
4. Contact administrator about server performance

### Browser Compatibility

Supported browsers:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

### Getting Help

#### Contact Information
- System Administrator: [Contact details to be provided]
- Technical Support: [Support contact information]
- User Documentation: This guide and online help

#### Reporting Issues
When reporting issues, please include:
1. Your username and role
2. Browser and version
3. Steps to reproduce the problem
4. Error messages (if any)
5. Screenshots (if helpful)

### Best Practices

#### Task Management
- Use clear, descriptive task titles
- Provide detailed descriptions
- Set realistic due dates
- Update status regularly
- Use comments for collaboration

#### Security
- Log out when finished
- Don't share login credentials
- Report suspicious activity
- Keep passwords secure

#### Performance
- Use filters to limit large result sets
- Close unused browser tabs
- Regularly clear browser cache
- Report performance issues promptly

---

## Conclusion

This Django Task Management System provides a comprehensive solution for organizing and tracking work within your organization. With its intuitive interface, powerful features, and detailed reporting capabilities, it helps teams stay organized and productive.

For additional support or feature requests, please contact your system administrator.

**Version**: 1.0  
**Last Updated**: June 2025  
**Documentation**: Complete User Guide

