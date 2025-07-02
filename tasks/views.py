# Fixed imports section - add proper spacing and error handling

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count
from django.utils import timezone
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import get_template
from django.contrib.auth.views import (
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView
)
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods

# External libraries with error handling
try:
    from xhtml2pdf import pisa
    import pdfkit
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    import xlsxwriter
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

import json
import csv
import html
import os
import io
from datetime import datetime, timedelta

from django.conf import settings
from django.utils.html import strip_tags

# Local imports - Fixed spacing
from .models import (
    User, Task, Comment, Division, TaskHistory, 
    Project, ProjectFile  # Fixed: added space before Project
)
from .forms import (
    DivisionForm, TaskForm, CustomUserCreationForm, 
    CustomAuthenticationForm, TaskFilterForm, CommentForm, 
    TaskUpdateForm, UserManagementForm, ProjectForm, ProjectFileForm
)


def home(request):
    """Home page - redirect to dashboard if logged in, otherwise show login"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')


def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                if not user.is_active:
                    messages.warning(request, 'Your account is awaiting admin approval. Please try again later.')
                    return redirect('login')
                login(request, user)
                messages.success(request, f'Welcome back, {user.first_name}!')
                return redirect('dashboard')  
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'registration/login.html', {'form': form})


def register_view(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Registration successful! You can now log in.')
            return redirect('login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})


def logout_view(request):
    """User logout view"""
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('login')


@login_required
def dashboard(request):
    """Enhanced dashboard view with role-based content"""
    try:
        user = request.user
        
        # Get user's tasks with safe role checking
        user_role = getattr(user, 'role', 'user')
        user_division = getattr(user, 'division', None)
        
        # Base task queryset based on role
        if user.is_super_admin():
            # Super admin sees all tasks
            all_tasks = Task.objects.all()
            managed_projects = Project.objects.all()[:5]  # Show recent 5 projects
        elif user.is_admin():
            # Admin sees tasks in their division
            if user_division:
                all_tasks = Task.objects.filter(division=user_division)
                # Admin sees projects they manage + projects in their division
                managed_projects = Project.objects.filter(
                    Q(assigned_to_admin=user) | Q(division=user_division)
                ).distinct()[:5]
            else:
                all_tasks = Task.objects.none()
                managed_projects = Project.objects.none()
        else:
            # Regular users see only their assigned tasks
            all_tasks = Task.objects.filter(assigned_to=user)
            managed_projects = Project.objects.none()
        
        # Task statistics
        total_tasks = all_tasks.count()
        pending_tasks = all_tasks.filter(status='pending').count()
        in_progress_tasks = all_tasks.filter(status='in_progress').count()
        completed_tasks = all_tasks.filter(status='completed').count()
        
        # Safe overdue tasks calculation
        try:
            overdue_tasks = all_tasks.filter(
                due_date__lt=timezone.now(),
                status__in=['pending', 'in_progress']
            ).count()
        except Exception:
            overdue_tasks = 0
        
        # Recent tasks (for the main section)
        recent_tasks = all_tasks.select_related('created_by', 'division', 'project').prefetch_related('assigned_to').order_by('-created_at')[:5]
        
        # My personal tasks (tasks specifically assigned to the current user)
        my_tasks = Task.objects.filter(assigned_to=user).select_related('project').prefetch_related('assigned_to').order_by('-created_at')[:5]
        
        context = {
            'total_tasks': total_tasks,
            'pending_tasks': pending_tasks,
            'in_progress_tasks': in_progress_tasks,
            'completed_tasks': completed_tasks,
            'overdue_tasks': overdue_tasks,
            'recent_tasks': recent_tasks,
            'my_tasks': my_tasks,
            'managed_projects': managed_projects,
        }
        
        return render(request, 'tasks/dashboard.html', context)
        
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Dashboard error for user {request.user}: {str(e)}")
        
        # Return a basic error page or redirect
        messages.error(request, 'An error occurred loading the dashboard. Please contact support.')
        return redirect('home')
       
@login_required
def task_list(request):
    """Task list view with filtering and search - UPDATED for multiple assignees"""
    user = request.user

    try:
        # Base queryset - CHANGED for M2M
        if user.is_admin():
            if user.is_super_admin():
                tasks = Task.objects.all()
            else:
                tasks = Task.objects.filter(division=user.division)
        else:
            tasks = Task.objects.filter(assigned_to=user)

        # Apply project filter if provided
        project_id = request.GET.get("project")
        if project_id:
            tasks = tasks.filter(project__id=project_id)
            project = get_object_or_404(Project, id=project_id)
        else:
            project = None

        # Apply filter form
        filter_form = TaskFilterForm(request.GET, user=user)
        if filter_form.is_valid():
            if filter_form.cleaned_data['status']:
                tasks = tasks.filter(status=filter_form.cleaned_data['status'])
            if filter_form.cleaned_data['priority']:
                tasks = tasks.filter(priority=filter_form.cleaned_data['priority'])
            if filter_form.cleaned_data['assigned_to']:
                # CHANGED: Filter by assigned users in M2M relationship
                tasks = tasks.filter(assigned_to=filter_form.cleaned_data['assigned_to'])
            if filter_form.cleaned_data['date_from']:
                tasks = tasks.filter(created_at__date__gte=filter_form.cleaned_data['date_from'])
            if filter_form.cleaned_data['date_to']:
                tasks = tasks.filter(created_at__date__lte=filter_form.cleaned_data['date_to'])

        # Search functionality - UPDATED for M2M
        search_query = request.GET.get('search')
        if search_query:
            tasks = tasks.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(assigned_to__username__icontains=search_query) |
                Q(assigned_to__first_name__icontains=search_query) |
                Q(assigned_to__last_name__icontains=search_query)
            ).distinct()

        # ADDED: Prefetch related to avoid N+1 queries
        tasks = tasks.select_related('created_by', 'division', 'project').prefetch_related('assigned_to')

        # Pagination
        paginator = Paginator(tasks.order_by('-created_at'), 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        # ADDED: Add permission data to each task for template
        for task in page_obj:
            task.user_can_edit = task.can_user_edit(user)
            task.user_is_assigned = task.is_assigned_to_user(user)
            task.user_can_update_status = task.is_assigned_to_user(user) or user.is_admin()

        context = {
            'page_obj': page_obj,
            'filter_form': filter_form,
            'search_query': search_query,
            'project': project,
        }

        return render(request, 'tasks/task_list.html', context)
        
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Task list error for user {request.user}: {str(e)}")
        
        messages.error(request, f'An error occurred loading tasks: {str(e)}')
        return redirect('dashboard')


@login_required
def task_detail(request, task_id):
    """Task detail view - UPDATED for multiple assignees"""
    try:
        task = get_object_or_404(Task, id=task_id)
        user = request.user
        
        # Check permissions - CHANGED for M2M
        if not user.is_admin() and not task.is_assigned_to_user(user):
            messages.error(request, 'You do not have permission to view this task.')
            return redirect('task_list')
        
        # Handle comment submission
        if request.method == 'POST':
            comment_form = CommentForm(request.POST, user=user)
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.task = task
                comment.user = user
                comment.save()
                
                # Create history entry
                TaskHistory.objects.create(
                    task=task,
                    user=user,
                    action='Comment added',
                    new_value=comment.content[:100] + '...' if len(comment.content) > 100 else comment.content
                )
                
                messages.success(request, 'Comment added successfully!')
                return redirect('task_detail', task_id=task.id)
        else:
            comment_form = CommentForm(user=user)
        
        # Get comments (filter internal comments for non-admins)
        comments = task.comments.all()
        if not user.is_admin():
            comments = comments.filter(is_internal=False)
        
        # Task update form for assigned user or admin - CHANGED for M2M
        update_form = None
        if task.is_assigned_to_user(user) or user.is_admin():
            update_form = TaskUpdateForm(instance=task)
        
        # ADDED: Pass permission checks to template
        context = {
            'task': task,
            'comments': comments,
            'comment_form': comment_form,
            'update_form': update_form,
            'user_can_edit': task.can_user_edit(user),
            'user_is_assigned': task.is_assigned_to_user(user),
            'user_can_update_status': task.is_assigned_to_user(user) or user.is_admin(),
        }
        
        return render(request, 'tasks/task_detail.html', context)
        
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Task detail error for user {request.user}, task {task_id}: {str(e)}")
        
        messages.error(request, f'An error occurred loading the task: {str(e)}')
        return redirect('task_list')
    
@login_required
def task_create(request, project_id=None):
    """Enhanced task creation with improved collaboration support"""
    user = request.user
    project = None

    # Handle project_id from URL parameter or GET parameter
    if not project_id:
        project_id = request.GET.get('project')
        if project_id:
            try:
                project_id = int(project_id)
            except (ValueError, TypeError):
                project_id = None

    if project_id:
        project = get_object_or_404(Project, id=project_id)
        
        # Enhanced permission check for task creation in projects
        can_create = False
        if user.is_super_admin():
            can_create = True
        elif user.is_admin() and (project.assigned_to_admin == user or project.division == user.division):
            can_create = True
        elif project.tasks.filter(assigned_to=user).exists():
            can_create = True
            
        if not can_create:
            messages.error(request, "You do not have permission to create tasks in this project.")
            return redirect("project_detail", project_id=project_id)

    if request.method == "POST":
        try:
            form = TaskForm(request.POST, user=user, project=project)
            
            if form.is_valid():
                try:
                    task = form.save(commit=False)
                    task.created_by = user
                    
                    # Save the task - form handles division assignment
                    task = form.save()

                    # Log task creation history
                    try:
                        assignees_names = ", ".join([u.get_display_name() for u in task.assigned_to.all()])
                        TaskHistory.objects.create(
                            task=task,
                            user=user,
                            action="Task created",
                            new_value=f'Task "{task.title}" created and assigned to: {assignees_names}'
                        )
                    except Exception as history_error:
                        print(f"History creation error: {history_error}")

                    messages.success(request, f"Task created successfully and assigned to {task.get_assignee_count()} user(s)!")
                    if project:
                        return redirect("project_detail", project_id=project.id)
                    return redirect("task_detail", task_id=task.id)
                    
                except Exception as save_error:
                    messages.error(request, f"Error saving task: {str(save_error)}")
                    print(f"Task save error: {save_error}")
            else:
                # IMPROVED ERROR HANDLING
                print(f"Form errors: {form.errors}")
                print(f"Form non-field errors: {form.non_field_errors}")
                
                # Display user-friendly error messages
                for field_name, field_errors in form.errors.items():
                    for error in field_errors:
                        if field_name == '__all__':
                            messages.error(request, f"{error}")
                        else:
                            field_label = form.fields.get(field_name, {}).label or field_name.replace('_', ' ').title()
                            messages.error(request, f"{field_label}: {error}")
                            
                # Log the detailed error for debugging
                if hasattr(form, '_division_source'):
                    print(f"Division source: {form._division_source}")
                    print(f"Target division: {form._target_division}")
                    print(f"Project: {project}")
                    print(f"User division: {user.division}")
                            
        except Exception as form_error:
            messages.error(request, f"Error processing form: {str(form_error)}")
            print(f"Form processing error: {form_error}")
            form = TaskForm(user=user, project=project)
    else:
        try:
            form = TaskForm(user=user, project=project)
        except Exception as form_init_error:
            messages.error(request, f"Error loading form: {str(form_init_error)}")
            print(f"Form initialization error: {form_init_error}")
            return redirect("project_detail", project_id=project_id) if project else redirect("task_list")

    context = {
        'form': form, 
        'title': f'Create Task in {project.title}' if project else 'Create Task',
        'project': project
    }
    return render(request, 'tasks/task_form.html', context)

@login_required
def task_edit(request, task_id):
    """Edit existing task - FIXED for M2M"""
    try:
        task = get_object_or_404(Task, id=task_id)
        user = request.user
        
        # Check permissions
        if not user.is_admin() and task.created_by != user and not task.is_assigned_to_user(user):
            messages.error(request, 'You do not have permission to edit this task.')
            return redirect('task_detail', task_id=task.id)
        
        if request.method == 'POST':
            form = TaskForm(request.POST, instance=task, user=user, project=task.project)
            if form.is_valid():
                # Store old values for history
                old_assignees = list(task.assigned_to.all())
                old_status = task.status
                old_priority = task.priority
                old_title = task.title
                
                task = form.save()
                
                # Create history entries for changes
                if old_title != task.title:
                    TaskHistory.objects.create(
                        task=task,
                        user=user,
                        action='Title changed',
                        old_value=old_title,
                        new_value=task.title
                    )
                
                if old_status != task.status:
                    TaskHistory.objects.create(
                        task=task,
                        user=user,
                        action='Status changed',
                        old_value=old_status,
                        new_value=task.status
                    )
                
                if old_priority != task.priority:
                    TaskHistory.objects.create(
                        task=task,
                        user=user,
                        action='Priority changed',
                        old_value=old_priority,
                        new_value=task.priority
                    )
                
                # Check for assignee changes
                new_assignees = list(task.assigned_to.all())
                if set(old_assignees) != set(new_assignees):
                    old_names = ", ".join([u.get_display_name() for u in old_assignees])
                    new_names = ", ".join([u.get_display_name() for u in new_assignees])
                    TaskHistory.objects.create(
                        task=task,
                        user=user,
                        action='Assignees changed',
                        old_value=old_names,
                        new_value=new_names
                    )
                
                messages.success(request, 'Task updated successfully!')
                return redirect('task_detail', task_id=task.id)
            else:
                # Show form errors
                for field_name, field_errors in form.errors.items():
                    for error in field_errors:
                        if field_name == '__all__':
                            messages.error(request, f"Form error: {error}")
                        else:
                            field_label = form.fields.get(field_name, {}).label or field_name
                            messages.error(request, f"{field_label}: {error}")
        else:
            form = TaskForm(instance=task, user=user, project=task.project)
        
        context = {
            'form': form, 
            'title': 'Edit Task', 
            'task': task,
            'project': task.project
        }
        return render(request, 'tasks/task_form.html', context)
        
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Task edit error for user {request.user}, task {task_id}: {str(e)}")
        
        messages.error(request, f'An error occurred editing the task: {str(e)}')
        return redirect('task_list')
    
@login_required
@require_POST
def task_update_status(request, task_id):
    """Update task status via AJAX - FIXED for M2M"""
    try:
        task = get_object_or_404(Task, id=task_id)
        user = request.user
        
        # FIXED: Check permissions for M2M relationship
        if not user.is_admin() and not task.is_assigned_to_user(user):
            return JsonResponse({'success': False, 'error': 'Permission denied'})
        
        data = json.loads(request.body)
        old_status = task.status
        new_status = data.get('status')
        actual_hours = data.get('actual_hours')
        
        if new_status in dict(Task.STATUS_CHOICES):
            task.status = new_status
            if actual_hours:
                task.actual_hours = actual_hours
            task.save()
            
            # Create history entry
            TaskHistory.objects.create(
                task=task,
                user=user,
                action='Status changed',
                old_value=old_status,
                new_value=new_status
            )
            
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'Invalid status'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    


from datetime import datetime
from django.utils.timezone import now

@login_required
def user_management(request):
    """Enhanced user management with role-based access control"""
    if not request.user.is_admin():
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')

    # Base queryset - IMPORTANT: Filter out super admins for regular admins
    if request.user.is_super_admin():
        # Super admin can see all users
        users = User.objects.all()
    else:
        # Regular admin can only see:
        # 1. Users in their division
        # 2. Exclude super_admin users (for security)
        users = User.objects.filter(
            division=request.user.division
        ).exclude(
            role='super_admin'  # CRITICAL: Hide super admins from regular admins
        )

    # Apply search filter
    search_query = request.GET.get('search')
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(users.order_by('username'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Statistics
    total_users = users.count()
    admin_count = users.filter(role='admin').count()
    active_users_count = users.filter(is_active=True).count()

    now_date = timezone.now()
    new_users_this_month = users.filter(
        date_joined__year=now_date.year,
        date_joined__month=now_date.month
    ).count()

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'total_users': total_users,
        'admin_count': admin_count,
        'new_users_this_month': new_users_this_month,
        'active_users_count': active_users_count,
        'user_can_see_all': request.user.is_super_admin(),  # For template logic
    }

    return render(request, 'tasks/user_management.html', context)


@login_required
def user_edit(request, user_id):
    """Enhanced user edit with role-based protection"""
    if not request.user.is_admin():
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    user_to_edit = get_object_or_404(User, id=user_id)

    # CRITICAL SECURITY CHECK: Prevent regular admins from editing super admins
    if not request.user.is_super_admin():
        # Regular admin restrictions:
        # 1. Can only edit users in their own division
        # 2. Cannot edit super_admin users
        if user_to_edit.division != request.user.division:
            messages.error(request, 'You can only edit users in your division.')
            return redirect('user_management')
        
        if user_to_edit.role == 'super_admin':
            messages.error(request, 'You do not have permission to edit this user.')
            return redirect('user_management')
    
    if request.method == 'POST':
        form = UserManagementForm(request.POST, instance=user_to_edit)
        if form.is_valid():
            # Additional security: prevent role escalation
            if not request.user.is_super_admin():
                # Regular admins cannot promote users to super_admin
                if form.cleaned_data.get('role') == 'super_admin':
                    messages.error(request, 'You cannot assign super admin role.')
                    return render(request, 'tasks/user_form.html', {
                        'form': form,
                        'user_to_edit': user_to_edit
                    })
            
            form.save()
            messages.success(request, f'User {user_to_edit.username} updated successfully!')
            return redirect('user_management')
    else:
        form = UserManagementForm(instance=user_to_edit)
        
        # Restrict role choices for regular admins
        if not request.user.is_super_admin():
            # Remove super_admin from choices
            form.fields['role'].choices = [
                choice for choice in form.fields['role'].choices 
                if choice[0] != 'super_admin'
            ]
    
    return render(request, 'tasks/user_form.html', {
        'form': form,
        'user_to_edit': user_to_edit
    })

# Reporting Views
from django.http import HttpResponse
from django.db.models import Q, Count, Avg
from datetime import datetime, timedelta
import xlsxwriter
import io
from django.utils import timezone

@login_required
def reports_dashboard(request):
    """Reports dashboard with various filters and export options"""
    # Get filter parameters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    division_id = request.GET.get('division')
    selected_statuses = request.GET.getlist('status')  # CHANGED: get list for multiple statuses
    project_id = request.GET.get('project')
    assigned_to = request.GET.get('assigned_to')
    
    # Base queryset with proper relationships - ADDED: prefetch comments
    tasks = Task.objects.select_related('created_by', 'division', 'project').prefetch_related('assigned_to', 'comments__user')
    
    # Apply filters based on user role
    if request.user.role == 'user':
        tasks = tasks.filter(Q(assigned_to=request.user) | Q(created_by=request.user)).distinct()
    elif request.user.role == 'admin':
        if request.user.division:
            tasks = tasks.filter(division=request.user.division)
        else:
            tasks = tasks.none()
    # Super admin can see all tasks
    
    # Apply date filters
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            tasks = tasks.filter(created_at__date__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            tasks = tasks.filter(created_at__date__lte=date_to_obj)
        except ValueError:
            pass
    
    # Apply other filters
    if division_id:
        tasks = tasks.filter(division_id=division_id)
    
    # CHANGED: Apply multiple status filters
    if selected_statuses:
        tasks = tasks.filter(status__in=selected_statuses)
    
    # Apply project filter
    if project_id:
        if project_id == 'no_project':
            tasks = tasks.filter(project__isnull=True)
        else:
            tasks = tasks.filter(project_id=project_id)
    
    if assigned_to:
        tasks = tasks.filter(assigned_to_id=assigned_to)
    
    # Calculate statistics
    total_tasks = tasks.count()
    completed_tasks = tasks.filter(status='completed').count()
    pending_tasks = tasks.filter(status='pending').count()
    in_progress_tasks = tasks.filter(status='in_progress').count()
    overdue_tasks = tasks.filter(
        due_date__lt=timezone.now(),
        status__in=['pending', 'in_progress']
    ).count()
    
    # Task distribution by division
    division_stats = tasks.values('division__name').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Task distribution by project
    project_stats = tasks.values('project__title').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Task distribution by status
    status_stats = tasks.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Average completion time for completed tasks
    completed_tasks_with_time = tasks.filter(
        status='completed',
        completed_at__isnull=False
    )
    
    avg_completion_time = None
    if completed_tasks_with_time.exists():
        total_time = sum([
            (task.completed_at - task.created_at).total_seconds() / 3600
            for task in completed_tasks_with_time
        ])
        avg_completion_time = total_time / completed_tasks_with_time.count()
    
    # Recent activity (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_tasks = tasks.filter(created_at__gte=thirty_days_ago)
    
    # Get projects for filter dropdown based on user role
    if request.user.role == 'user':
        projects = Project.objects.filter(
            tasks__assigned_to=request.user
        ).distinct().order_by('title')
    elif request.user.role == 'admin':
        if request.user.division:
            projects = Project.objects.filter(
                Q(division=request.user.division) | Q(assigned_to_admin=request.user)
            ).distinct().order_by('title')
        else:
            projects = Project.objects.none()
    else:
        projects = Project.objects.all().order_by('title')
    
    # ADDED: Process tasks to add latest comment for in_progress tasks
    tasks_list = list(tasks.order_by('-created_at')[:20])
    for task in tasks_list:
        if task.status == 'in_progress':
            # Get the latest comment for this task
            latest_comment = task.comments.filter(
                is_internal=False  # Only public comments
            ).order_by('-created_at').first()
            task.latest_comment = latest_comment
        else:
            task.latest_comment = None
    
    context = {
        'tasks': tasks_list,  # Latest 20 tasks for preview with comments
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'pending_tasks': pending_tasks,
        'in_progress_tasks': in_progress_tasks,
        'overdue_tasks': overdue_tasks,
        'division_stats': division_stats,
        'project_stats': project_stats,
        'status_stats': status_stats,
        'avg_completion_time': avg_completion_time,
        'recent_tasks_count': recent_tasks.count(),
        'divisions': Division.objects.all(),
        'projects': projects,
        'users': User.objects.filter(is_active=True),
        'date_from': date_from,
        'date_to': date_to,
        'selected_division': division_id,
        'selected_statuses': selected_statuses,  # CHANGED: list of statuses
        'selected_project': project_id,
        'selected_assigned_to': assigned_to,
    }
    
    return render(request, 'tasks/reports.html', context)

@login_required
def export_tasks_excel(request):
    """Export filtered tasks to Excel format with comment support."""
    try:
        # Get filters
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        division_id = request.GET.get('division')
        selected_statuses = request.GET.getlist('status')  # CHANGED: multiple statuses
        project_id = request.GET.get('project')
        assigned_to = request.GET.get('assigned_to')

        # Queryset with proper prefetch for M2M and comments
        tasks = Task.objects.select_related('created_by', 'division', 'project').prefetch_related('assigned_to', 'comments__user')

        # Role-based filter
        if request.user.role == 'user':
            tasks = tasks.filter(Q(assigned_to=request.user) | Q(created_by=request.user)).distinct()
        elif request.user.role == 'admin':
            if request.user.division:
                tasks = tasks.filter(division=request.user.division)
            else:
                tasks = tasks.none()

        # Apply filters
        if date_from:
            try:
                tasks = tasks.filter(created_at__date__gte=datetime.strptime(date_from, '%Y-%m-%d').date())
            except ValueError:
                pass
        if date_to:
            try:
                tasks = tasks.filter(created_at__date__lte=datetime.strptime(date_to, '%Y-%m-%d').date())
            except ValueError:
                pass
        if division_id:
            tasks = tasks.filter(division_id=division_id)
        
        # CHANGED: Apply multiple status filters
        if selected_statuses:
            tasks = tasks.filter(status__in=selected_statuses)
        
        # Apply project filter
        if project_id:
            if project_id == 'no_project':
                tasks = tasks.filter(project__isnull=True)
            else:
                tasks = tasks.filter(project_id=project_id)
        
        if assigned_to:
            tasks = tasks.filter(assigned_to_id=assigned_to)

        # Check if xlsxwriter is available
        if not EXCEL_AVAILABLE:
            messages.error(request, 'Excel export is not available. Please contact administrator.')
            return redirect('reports_dashboard')

        # Prepare Excel workbook
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True, 'remove_timezone': True})
        tasks_sheet = workbook.add_worksheet('Tasks')
        summary_sheet = workbook.add_worksheet('Summary')

        # Formats
        header_format = workbook.add_format({'bold': True, 'bg_color': '#4f46e5', 'font_color': 'white', 'border': 1})
        cell_format = workbook.add_format({'border': 1, 'text_wrap': True})
        date_format = workbook.add_format({'border': 1, 'num_format': 'yyyy-mm-dd hh:mm'})
        comment_format = workbook.add_format({'border': 1, 'text_wrap': True, 'bg_color': '#f0f9ff'})

        # Headers - UPDATED: Comments instead of Created Date
        tasks_headers = [
            'ID', 'Title', 'Description', 'Status', 'Project', 'Division',
            'Created By', 'Assigned To', 'Team Size', 'Due Date',
            'Latest Comment', 'Estimated Hours', 'Actual Hours'
        ]
        for col, header in enumerate(tasks_headers):
            tasks_sheet.write(0, col, header, header_format)

        # Data rows
        for row, task in enumerate(tasks.order_by('-created_at'), 1):
            try:
                # Clean description
                cleaned_description = html.unescape(strip_tags(task.description or ''))
                
                # Get assignees safely
                assignees = task.assigned_to.all()
                if assignees.exists():
                    assignee_names = ", ".join([
                        user.get_full_name() or user.username 
                        for user in assignees
                    ])
                    team_size = assignees.count()
                else:
                    assignee_names = 'Unassigned'
                    team_size = 0

                # Get latest comment for in_progress tasks
                latest_comment_text = ''
                if task.status == 'in_progress':
                    latest_comment = task.comments.filter(is_internal=False).order_by('-created_at').first()
                    if latest_comment:
                        comment_user = latest_comment.user.get_full_name() or latest_comment.user.username
                        comment_content = html.unescape(strip_tags(latest_comment.content))
                        latest_comment_text = f"{comment_user}: {comment_content[:200]}..."
                    else:
                        latest_comment_text = 'No comments yet'
                elif task.status in ['completed', 'pending', 'cancelled']:
                    latest_comment_text = '-'

                # Write row data
                tasks_sheet.write(row, 0, task.id, cell_format)
                tasks_sheet.write(row, 1, task.title, cell_format)
                tasks_sheet.write(row, 2, cleaned_description[:500] + '...' if len(cleaned_description) > 500 else cleaned_description, cell_format)
                tasks_sheet.write(row, 3, task.get_status_display(), cell_format)
                tasks_sheet.write(row, 4, task.project.title if task.project else 'Individual Task', cell_format)
                tasks_sheet.write(row, 5, task.division.name if task.division else 'N/A', cell_format)
                tasks_sheet.write(row, 6, task.created_by.get_full_name() if task.created_by else 'N/A', cell_format)
                tasks_sheet.write(row, 7, assignee_names, cell_format)
                tasks_sheet.write(row, 8, team_size, cell_format)
                tasks_sheet.write(row, 9, task.due_date if task.due_date else 'N/A', date_format)
                tasks_sheet.write(row, 10, latest_comment_text, comment_format if task.status == 'in_progress' else cell_format)
                tasks_sheet.write(row, 11, task.estimated_hours if task.estimated_hours else 'N/A', cell_format)
                tasks_sheet.write(row, 12, task.actual_hours if task.actual_hours else 'N/A', cell_format)
                
            except Exception as e:
                print(f"Error processing task {task.id}: {e}")
                continue

        # Column widths - UPDATED: Adjusted for comment column
        column_widths = [8, 30, 50, 12, 25, 15, 20, 30, 10, 18, 40, 15, 15]
        for col, width in enumerate(column_widths):
            tasks_sheet.set_column(col, col, width)

        # Summary Sheet
        summary_data = [
            ['Metric', 'Value'],
            ['Total Tasks', tasks.count()],
            ['Completed Tasks', tasks.filter(status='completed').count()],
            ['Pending Tasks', tasks.filter(status='pending').count()],
            ['In Progress Tasks', tasks.filter(status='in_progress').count()],
            ['Overdue Tasks', tasks.filter(due_date__lt=timezone.now(), status__in=['pending', 'in_progress']).count()],
        ]
        
        for row, (metric, value) in enumerate(summary_data):
            if row == 0:
                summary_sheet.write(row, 0, metric, header_format)
                summary_sheet.write(row, 1, value, header_format)
            else:
                summary_sheet.write(row, 0, metric, cell_format)
                summary_sheet.write(row, 1, value, cell_format)

        summary_sheet.set_column('A:A', 20)
        summary_sheet.set_column('B:B', 15)

        workbook.close()
        output.seek(0)

        # Response
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f'tasks_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Excel export error: {str(e)}")
        
        messages.error(request, f'Error generating Excel report: {str(e)}')
        return redirect('reports_dashboard')
        
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

# Replace/add these views in your views.py

from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
import logging

logger = logging.getLogger(__name__)

@login_required
@require_POST  
def toggle_user_status(request, user_id):
    """Toggle user active status via AJAX - IMPROVED VERSION"""
    try:
        # Check if current user is admin
        if not request.user.is_admin():
            return JsonResponse({
                'success': False, 
                'message': 'You do not have permission to perform this action.'
            }, status=403)

        # Get the user to toggle
        user_to_toggle = get_object_or_404(User, id=user_id)

        # Prevent user from deactivating themselves
        if user_to_toggle == request.user:
            return JsonResponse({
                'success': False, 
                'message': 'You cannot deactivate yourself.'
            }, status=400)

        # Security check: Regular admins cannot toggle super admins
        if not request.user.is_super_admin() and user_to_toggle.role == 'super_admin':
            return JsonResponse({
                'success': False, 
                'message': 'You do not have permission to modify this user.'
            }, status=403)

        # Security check: Regular admins can only toggle users in their division
        if not request.user.is_super_admin():
            if user_to_toggle.division != request.user.division:
                return JsonResponse({
                    'success': False, 
                    'message': 'You can only manage users in your division.'
                }, status=403)

        # Store old status for logging
        old_status = user_to_toggle.is_active
        
        # Toggle the status
        user_to_toggle.is_active = not old_status
        user_to_toggle.save(update_fields=['is_active'])  # Only update the specific field

        # Prepare response message
        action = "activated" if user_to_toggle.is_active else "deactivated"
        message = f'User "{user_to_toggle.get_full_name() or user_to_toggle.username}" has been {action} successfully.'

        # Log the action
        logger.info(f'User {request.user.username} {action} user {user_to_toggle.username}')

        return JsonResponse({
            'success': True,
            'new_status': user_to_toggle.is_active,
            'message': message,
            'user_id': user_to_toggle.id,
            'action': action
        })

    except User.DoesNotExist:
        logger.warning(f'Attempt to toggle non-existent user {user_id} by {request.user.username}')
        return JsonResponse({
            'success': False, 
            'message': 'User not found.'
        }, status=404)
    
    except Exception as e:
        # Log the detailed error
        logger.error(f'Error toggling user status for user {user_id} by {request.user.username}: {str(e)}', exc_info=True)
        
        return JsonResponse({
            'success': False, 
            'message': f'An error occurred: {str(e)}'
        }, status=500)


@login_required
@require_POST
def delete_user(request, user_id):
    """Delete user via AJAX - NEW FUNCTION"""
    try:
        # Check if current user is admin
        if not request.user.is_admin():
            return JsonResponse({
                'success': False, 
                'message': 'You do not have permission to perform this action.'
            }, status=403)

        # Get the user to delete
        user_to_delete = get_object_or_404(User, id=user_id)

        # Prevent user from deleting themselves
        if user_to_delete == request.user:
            return JsonResponse({
                'success': False, 
                'message': 'You cannot delete yourself.'
            }, status=400)

        # Security check: Regular admins cannot delete super admins
        if not request.user.is_super_admin() and user_to_delete.role == 'super_admin':
            return JsonResponse({
                'success': False, 
                'message': 'You do not have permission to delete this user.'
            }, status=403)

        # Security check: Regular admins can only delete users in their division
        if not request.user.is_super_admin():
            if user_to_delete.division != request.user.division:
                return JsonResponse({
                    'success': False, 
                    'message': 'You can only manage users in your division.'
                }, status=403)

        # Store user info for response
        user_name = user_to_delete.get_full_name() or user_to_delete.username
        username = user_to_delete.username

        # Check if user has any tasks assigned (optional warning)
        assigned_tasks_count = user_to_delete.assigned_tasks.count()
        created_tasks_count = user_to_delete.created_tasks.count()

        # Delete the user
        user_to_delete.delete()

        # Log the action
        logger.info(f'User {request.user.username} deleted user {username}')

        message = f'User "{user_name}" has been deleted successfully.'
        if assigned_tasks_count > 0 or created_tasks_count > 0:
            message += f' ({assigned_tasks_count} assigned tasks and {created_tasks_count} created tasks were also affected.)'

        return JsonResponse({
            'success': True,
            'message': message,
            'user_id': user_id,
            'deleted_user': user_name
        })

    except User.DoesNotExist:
        logger.warning(f'Attempt to delete non-existent user {user_id} by {request.user.username}')
        return JsonResponse({
            'success': False, 
            'message': 'User not found.'
        }, status=404)
    
    except Exception as e:
        # Log the detailed error
        logger.error(f'Error deleting user {user_id} by {request.user.username}: {str(e)}', exc_info=True)
        
        return JsonResponse({
            'success': False, 
            'message': f'An error occurred while deleting user: {str(e)}'
        }, status=500)
    
def division_list(request):
    divisions = Division.objects.all()
    return render(request, 'divisions/division_list.html', {'divisions': divisions})

def create_division(request):
    if request.method == 'POST':
        form = DivisionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Division created successfully.")
            return redirect('division_list')
    else:
        form = DivisionForm()
    return render(request, 'divisions/division_form.html', {'form': form, 'title': 'Create Division'})

def edit_division(request, pk):
    division = get_object_or_404(Division, pk=pk)
    if request.method == 'POST':
        form = DivisionForm(request.POST, instance=division)
        if form.is_valid():
            form.save()
            messages.success(request, "Division updated successfully.")
            return redirect('division_list')
    else:
        form = DivisionForm(instance=division)
    return render(request, 'divisions/division_form.html', {'form': form, 'title': 'Edit Division'})

def delete_division(request, pk):
    division = get_object_or_404(Division, pk=pk)
    if request.method == 'POST':
        division.delete()
        messages.success(request, "Division deleted successfully.")
        return redirect('division_list')
    return render(request, 'divisions/division_confirm_delete.html', {'division': division})

@login_required
def export_tasks_pdf(request):
    """Export filtered tasks to PDF format with comment support"""
    try:
        # Check if PDF libraries are available
        if not PDF_AVAILABLE:
            messages.error(request, 'PDF export is not available. Please contact administrator.')
            return redirect('reports_dashboard')

        # Extract filters
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        division_id = request.GET.get('division')
        selected_statuses = request.GET.getlist('status')  # CHANGED: multiple statuses
        project_id = request.GET.get('project')
        assigned_to = request.GET.get('assigned_to')

        # Base queryset with proper relationships and comments
        tasks_qs = Task.objects.select_related('created_by', 'division', 'project').prefetch_related('assigned_to', 'comments__user')

        # Role-based filtering
        if request.user.role == 'user':
            tasks_qs = tasks_qs.filter(Q(assigned_to=request.user) | Q(created_by=request.user)).distinct()
        elif request.user.role == 'admin':
            if request.user.division:
                tasks_qs = tasks_qs.filter(division=request.user.division)
            else:
                tasks_qs = tasks_qs.none()

        # Apply filters with error handling
        try:
            if date_from:
                tasks_qs = tasks_qs.filter(created_at__date__gte=datetime.strptime(date_from, '%Y-%m-%d').date())
            if date_to:
                tasks_qs = tasks_qs.filter(created_at__date__lte=datetime.strptime(date_to, '%Y-%m-%d').date())
        except ValueError as e:
            messages.error(request, f'Invalid date format: {str(e)}')
            return redirect('reports_dashboard')

        if division_id:
            tasks_qs = tasks_qs.filter(division_id=division_id)
        
        # CHANGED: Apply multiple status filters
        if selected_statuses:
            tasks_qs = tasks_qs.filter(status__in=selected_statuses)
        
        # Apply project filter
        if project_id:
            if project_id == 'no_project':
                tasks_qs = tasks_qs.filter(project__isnull=True)
            else:
                tasks_qs = tasks_qs.filter(project_id=project_id)
        
        if assigned_to:
            tasks_qs = tasks_qs.filter(assigned_to_id=assigned_to)

        # Convert queryset to list AFTER filtering
        tasks = list(tasks_qs.order_by('-created_at'))

        # Process tasks for template
        collaborative_count = 0
        total_assignees = 0
        
        for task in tasks:
            try:
                # Clean description
                task.description_clean = html.unescape(strip_tags(task.description or ''))
                
                # Get assignees and calculate stats
                assignees = list(task.assigned_to.all())
                task.assignee_count = len(assignees)
                total_assignees += task.assignee_count
                
                # Check if collaborative (more than 1 assignee)
                task.is_collaborative = task.assignee_count > 1
                if task.is_collaborative:
                    collaborative_count += 1
                
                # Prepare assignee names
                if assignees:
                    task.assignee_names = ", ".join([
                        user.get_full_name() or user.username 
                        for user in assignees
                    ])
                else:
                    task.assignee_names = "Unassigned"
                
                # ADDED: Get latest comment for in_progress tasks
                if task.status == 'in_progress':
                    latest_comment = task.comments.filter(is_internal=False).order_by('-created_at').first()
                    task.latest_comment = latest_comment
                else:
                    task.latest_comment = None
                    
            except Exception as e:
                print(f"Error processing task {task.id}: {e}")
                # Set safe defaults
                task.description_clean = "Error loading description"
                task.assignee_names = "Error loading assignees"
                task.assignee_count = 0
                task.is_collaborative = False
                task.latest_comment = None

        # Get division and project information
        selected_division_obj = None
        if division_id:
            try:
                selected_division_obj = Division.objects.get(id=division_id)
            except Division.DoesNotExist:
                pass

        selected_project_obj = None
        if project_id and project_id != 'no_project':
            try:
                selected_project_obj = Project.objects.get(id=project_id)
            except Project.DoesNotExist:
                pass

        # Prepare logo path with better error handling
        logo_path = None
        try:
            static_logo_path = os.path.join(settings.STATIC_ROOT or settings.BASE_DIR, 'static', 'images', 'logo.png')
            if os.path.exists(static_logo_path):
                logo_path = f'file:///{static_logo_path.replace(os.sep, "/")}'
            else:
                base_logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')
                if os.path.exists(base_logo_path):
                    logo_path = f'file:///{base_logo_path.replace(os.sep, "/")}'
                else:
                    logo_path = None
        except Exception as e:
            print(f"Logo path error: {e}")
            logo_path = None

        # Render HTML template
        template = get_template('tasks/pdf_template.html')
        context = {
            'tasks': tasks,
            'generated_at': timezone.now(),
            'logo_path': logo_path,
            'user': request.user,
            'divisions': Division.objects.all(),
            'projects': Project.objects.all(),
            'selected_division': division_id,
            'selected_division_obj': selected_division_obj,
            'selected_project': project_id,
            'selected_project_obj': selected_project_obj,
            'selected_statuses': selected_statuses,  # CHANGED: list of statuses
            'date_from': date_from,
            'date_to': date_to,
            'selected_assigned_to': assigned_to,
            'collaborative_count': collaborative_count,
            'total_assignees': total_assignees,
        }
        
        rendered_html = template.render(context)

        # PDF generation with error handling
        try:
            if hasattr(settings, 'WKHTMLTOPDF_PATH') and settings.WKHTMLTOPDF_PATH:
                config = pdfkit.configuration(wkhtmltopdf=settings.WKHTMLTOPDF_PATH)
            else:
                config = None
                
            options = {
                'enable-local-file-access': None,
                'encoding': 'UTF-8',
                'quiet': '',
                'no-outline': None,
                'margin-top': '0.75in',
                'margin-right': '0.75in',
                'margin-bottom': '0.75in',
                'margin-left': '0.75in',
            }

            pdf = pdfkit.from_string(rendered_html, False, options=options, configuration=config)

        except Exception as pdf_error:
            print(f"PDF generation error: {pdf_error}")
            messages.error(request, f'Error generating PDF: {str(pdf_error)}')
            return redirect('reports_dashboard')

        # Return response
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f'tasks_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"PDF export error: {str(e)}")
        
        messages.error(request, f'Error generating PDF report: {str(e)}')
        return redirect('reports_dashboard')


@login_required
def delete_task(request, task_id):
    """Delete task - FIXED with proper error handling"""
    try:
        task = get_object_or_404(Task, id=task_id)

        if not request.user.is_admin() and task.created_by != request.user:
            messages.error(request, 'You do not have permission to delete this task.')
            return redirect('task_detail', task_id=task.id)

        task_title = task.title
        project = task.project
        task.delete()
        
        messages.success(request, f'Task "{task_title}" deleted successfully.')
        
        # Redirect to project if task was part of a project, otherwise to task list
        if project:
            return redirect('project_detail', project_id=project.id)
        return redirect('task_list')
        
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Task delete error for user {request.user}, task {task_id}: {str(e)}")
        
        messages.error(request, f'An error occurred deleting the task: {str(e)}')
        return redirect('task_list')
    
class CustomPasswordResetView(PasswordResetView):
    template_name = 'registration/password_reset_form.html'
    email_template_name = 'registration/password_reset_email.html'
    subject_template_name = 'registration/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')

class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'registration/password_reset_done.html'

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'registration/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')

class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'registration/password_reset_complete.html'

@login_required
def project_list(request):
    """List projects based on user role and access permissions"""
    user = request.user
    
    try:
        if user.is_super_admin():
            # Super admin sees all projects
            projects = Project.objects.all()
        elif user.is_admin():
            # Admin sees projects they manage or in their division
            projects = Project.objects.filter(
                Q(assigned_to_admin=user) | Q(division=user.division)
            ).distinct()
        else:
            # Regular users see projects where they have assigned tasks
            projects = Project.objects.filter(
                tasks__assigned_to=user
            ).distinct()

        # Apply search filter BEFORE adding attributes
        search_query = request.GET.get("search")
        if search_query:
            projects = projects.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(assigned_to_admin__username__icontains=search_query) |
                Q(assigned_to_admin__first_name__icontains=search_query) |
                Q(assigned_to_admin__last_name__icontains=search_query) |
                Q(division__name__icontains=search_query)
            ).distinct()

        # Convert to list to avoid repeated queries
        projects_list = list(projects.select_related('division', 'assigned_to_admin').prefetch_related('tasks__assigned_to'))

        # Add project statistics AFTER getting the list
        for project in projects_list:
            try:
                # Safely calculate statistics
                all_tasks = project.tasks.all()
                project.total_tasks = all_tasks.count()
                project.completed_tasks = all_tasks.filter(status='completed').count()
                
                if not user.is_super_admin():
                    project.my_tasks = all_tasks.filter(assigned_to=user).count()
                else:
                    project.my_tasks = 0
                
                # Use the model method
                project.progress = project.get_progress_percentage()
                
            except Exception as e:
                # Fallback values if there's an error
                project.total_tasks = 0
                project.completed_tasks = 0
                project.my_tasks = 0
                project.progress = 0
                print(f"Error calculating stats for project {project.id}: {e}")

        # Pagination
        paginator = Paginator(projects_list, 12)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        context = {
            "page_obj": page_obj,
            "search_query": search_query,
            "user_role": user.role,
        }
        return render(request, "tasks/project_list.html", context)
        
    except Exception as e:
        messages.error(request, f"Error loading projects: {str(e)}")
        return redirect("dashboard")
    
@login_required
def project_create(request):
    """Create a new project (Super Admin only)"""
    if not request.user.is_super_admin():
        messages.error(request, "You do not have permission to create projects.")
        return redirect("project_list")

    if request.method == "POST":
        try:
            form = ProjectForm(request.POST, user=request.user)
            if form.is_valid():
                project = form.save(commit=False)
                project.created_by = request.user
                project.save()
                messages.success(request, f"Project '{project.title}' created successfully!")
                return redirect("project_detail", project_id=project.id)
            else:
                # Show specific form errors
                for field_name, field_errors in form.errors.items():
                    for error in field_errors:
                        if field_name == '__all__':
                            messages.error(request, f"Form error: {error}")
                        else:
                            field_label = form.fields.get(field_name, {}).label or field_name
                            messages.error(request, f"{field_label}: {error}")
                            
        except Exception as e:
            messages.error(request, f"Error creating project: {str(e)}")
    else:
        form = ProjectForm(user=request.user)

    return render(request, "tasks/project_form.html", {
        "form": form, 
        "title": "Create Project"
    })
@login_required
def project_detail(request, project_id):
    """Enhanced project detail view with comprehensive access control"""
    try:
        project = get_object_or_404(Project, id=project_id)
        user = request.user

        # Enhanced permission checking
        can_view = False
        can_edit = False
        can_create_tasks = False
        can_manage_files = False
        is_project_admin = False
        
        # Determine permissions based on user role
        if user.is_super_admin():
            can_view = can_edit = can_create_tasks = can_manage_files = True
        elif user.is_admin():
            if project.assigned_to_admin == user:
                can_view = can_edit = can_create_tasks = can_manage_files = True
                is_project_admin = True
            elif project.division == user.division:
                can_view = can_create_tasks = can_manage_files = True
        else:
            # Regular user - can view if they have tasks in this project
            if project.tasks.filter(assigned_to=user).exists():
                can_view = True
                can_create_tasks = True

        if not can_view:
            messages.error(request, "You do not have permission to view this project.")
            return redirect("project_list")

        # Get tasks with enhanced filtering
        tasks = project.tasks.all().select_related('created_by').prefetch_related('assigned_to')

        # Get project files
        files = project.files.all().order_by("-uploaded_at")

        # Handle file upload
        file_form = None
        if request.method == "POST" and can_manage_files:
            file_form = ProjectFileForm(request.POST, request.FILES)
            if file_form.is_valid():
                try:
                    project_file = file_form.save(commit=False)
                    project_file.project = project
                    project_file.uploaded_by = user
                    project_file.filename = project_file.file.name
                    project_file.file_size = project_file.file.size
                    project_file.save()
                    messages.success(request, "File uploaded successfully!")
                    return redirect("project_detail", project_id=project.id)
                except Exception as e:
                    messages.error(request, f"Error uploading file: {str(e)}")
        else:
            if can_manage_files:
                file_form = ProjectFileForm()

        # Project statistics
        total_tasks = tasks.count()
        completed_tasks = tasks.filter(status='completed').count()
        pending_tasks = tasks.filter(status='pending').count()
        in_progress_tasks = tasks.filter(status='in_progress').count()
        
        # User-specific stats
        if not user.is_super_admin():
            user_tasks = tasks.filter(assigned_to=user)
        else:
            user_tasks = tasks
            
        user_completed = user_tasks.filter(status='completed').count()
        user_pending = user_tasks.filter(status='pending').count()

        context = {
            "project": project,
            "tasks": tasks.order_by('-created_at'),
            "files": files,
            "file_form": file_form,
            
            # Permission flags for template
            "can_edit": can_edit,
            "can_create_tasks": can_create_tasks,
            "can_manage_files": can_manage_files,
            "is_project_admin": is_project_admin,
            
            # User role flags for template (if needed)
            "user_is_admin": user.is_admin(),
            "user_is_super_admin": user.is_super_admin(),
            
            # Statistics
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "in_progress_tasks": in_progress_tasks,
            "user_tasks_count": user_tasks.count(),
            "user_completed": user_completed,
            "user_pending": user_pending,
            "progress_percentage": project.get_progress_percentage(),
        }
        return render(request, "tasks/project_detail.html", context)
        
    except Exception as e:
        messages.error(request, f"Error loading project: {str(e)}")
        return redirect("project_list")


@login_required
def project_edit(request, project_id):
    """Edit project details (Super Admin or assigned Admin)"""
    try:
        project = get_object_or_404(Project, id=project_id)

        if not (request.user.is_super_admin() or (request.user.is_admin() and project.assigned_to_admin == request.user)):
            messages.error(request, "You do not have permission to edit this project.")
            return redirect("project_detail", project_id=project.id)

        if request.method == "POST":
            form = ProjectForm(request.POST, instance=project, user=request.user)
            if form.is_valid():
                form.save()
                messages.success(request, "Project updated successfully!")
                return redirect("project_detail", project_id=project.id)
            else:
                messages.error(request, "Please correct the errors below.")
        else:
            form = ProjectForm(instance=project, user=request.user)

        return render(request, "tasks/project_form.html", {"form": form, "title": "Edit Project", "project": project})
        
    except Exception as e:
        messages.error(request, f"Error editing project: {str(e)}")
        return redirect("project_list")


@login_required
@require_POST
def project_delete(request, project_id):
    """Delete a project (Super Admin only)"""
    if not request.user.is_super_admin():
        messages.error(request, "You do not have permission to delete projects.")
        return redirect("project_list")

    try:
        project = get_object_or_404(Project, id=project_id)
        project_title = project.title
        project.delete()
        messages.success(request, f"Project '{project_title}' deleted successfully!")
    except Exception as e:
        messages.error(request, f"Error deleting project: {str(e)}")
    
    return redirect("project_list")


@login_required
@require_POST
def project_file_delete(request, file_id):
    """Delete a project file (Super Admin or project creator)"""
    try:
        project_file = get_object_or_404(ProjectFile, id=file_id)
        user = request.user

        if not (user.is_super_admin() or project_file.project.created_by == user):
            messages.error(request, "You do not have permission to delete this file.")
            return redirect("project_detail", project_id=project_file.project.id)

        project_id = project_file.project.id
        filename = project_file.filename
        project_file.delete()
        messages.success(request, f"File '{filename}' deleted successfully!")
        return redirect("project_detail", project_id=project_id)
        
    except Exception as e:
        messages.error(request, f"Error deleting file: {str(e)}")
        return redirect("project_list")


@login_required
def get_division_admins(request):
    """AJAX view to get admins for a specific division"""
    if not request.user.is_super_admin():
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    division_id = request.GET.get('division_id')
    if not division_id:
        return JsonResponse({'admins': []})
    
    try:
        admins = User.objects.filter(
            division_id=division_id,
            role__in=['admin', 'super_admin'],
            is_active=True
        ).values('id', 'username', 'first_name', 'last_name')
        
        admin_list = [
            {
                'id': admin['id'],
                'name': f"{admin['first_name']} {admin['last_name']} ({admin['username']})" 
                       if admin['first_name'] and admin['last_name'] 
                       else admin['username']
            }
            for admin in admins
        ]
        
        return JsonResponse({'admins': admin_list})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def my_projects(request):
    """View for users to see their assigned projects and tasks"""
    user = request.user
    
    # Get projects where user has assigned tasks
    projects = Project.objects.filter(
        tasks__assigned_to=user
    ).distinct().select_related('division', 'assigned_to_admin')
    
    # Add task statistics for each project
    project_stats = []
    for project in projects:
        user_tasks = project.tasks.filter(assigned_to=user)
        stats = {
            'project': project,
            'total_tasks': user_tasks.count(),
            'completed_tasks': user_tasks.filter(status='completed').count(),
            'pending_tasks': user_tasks.filter(status='pending').count(),
            'in_progress_tasks': user_tasks.filter(status='in_progress').count(),
            'overdue_tasks': user_tasks.filter(
                due_date__lt=timezone.now(),
                status__in=['pending', 'in_progress']
            ).count(),
        }
        stats['progress'] = (
            (stats['completed_tasks'] / stats['total_tasks'] * 100) 
            if stats['total_tasks'] > 0 else 0
        )
        project_stats.append(stats)
    
    context = {
        'project_stats': project_stats,
        'total_projects': len(project_stats),
    }
    return render(request, 'tasks/my_projects.html', context)


# Add this view to your views.py

import os
import mimetypes
from django.http import Http404, FileResponse
from django.utils.encoding import smart_str

@login_required
def download_project_file(request, file_id):
    """Download project file with permission checking"""
    try:
        project_file = get_object_or_404(ProjectFile, id=file_id)
        user = request.user
        
        # Check permissions
        can_access = False
        if user.is_super_admin():
            can_access = True
        elif user.is_admin() and project_file.project.division == user.division:
            can_access = True
        elif project_file.project.tasks.filter(assigned_to=user).exists():
            can_access = True
        elif project_file.uploaded_by == user:
            can_access = True
            
        if not can_access:
            messages.error(request, "You don't have permission to access this file.")
            return redirect('project_detail', project_id=project_file.project.id)
        
        # Get the file path
        try:
            file_path = project_file.file.path
            if not os.path.exists(file_path):
                messages.error(request, "File not found on server.")
                return redirect('project_detail', project_id=project_file.project.id)
        except ValueError:
            # Handle case where file field is empty
            messages.error(request, "File path is invalid.")
            return redirect('project_detail', project_id=project_file.project.id)
        
        # Determine content type
        content_type, encoding = mimetypes.guess_type(file_path)
        if content_type is None:
            content_type = 'application/octet-stream'
        
        # Create response
        try:
            response = FileResponse(
                open(file_path, 'rb'),
                content_type=content_type,
                as_attachment=True,
                filename=smart_str(project_file.filename)
            )
            return response
        except IOError:
            messages.error(request, "Error reading file from server.")
            return redirect('project_detail', project_id=project_file.project.id)
            
    except ProjectFile.DoesNotExist:
        messages.error(request, "File not found.")
        return redirect('project_list')
    except Exception as e:
        messages.error(request, f"Error downloading file: {str(e)}")
        return redirect('project_list')


@login_required 
def view_project_file(request, file_id):
    """View project file inline (for images, PDFs, text files)"""
    try:
        project_file = get_object_or_404(ProjectFile, id=file_id)
        user = request.user
        
        # Check permissions (same as download)
        can_access = False
        if user.is_super_admin():
            can_access = True
        elif user.is_admin() and project_file.project.division == user.division:
            can_access = True
        elif project_file.project.tasks.filter(assigned_to=user).exists():
            can_access = True
        elif project_file.uploaded_by == user:
            can_access = True
            
        if not can_access:
            messages.error(request, "You don't have permission to access this file.")
            return redirect('project_detail', project_id=project_file.project.id)
        
        # Get the file path
        try:
            file_path = project_file.file.path
            if not os.path.exists(file_path):
                messages.error(request, "File not found on server.")
                return redirect('project_detail', project_id=project_file.project.id)
        except ValueError:
            messages.error(request, "File path is invalid.")
            return redirect('project_detail', project_id=project_file.project.id)
        
        # Determine content type
        content_type, encoding = mimetypes.guess_type(file_path)
        if content_type is None:
            content_type = 'application/octet-stream'
        
        # Create response for inline viewing
        try:
            response = FileResponse(
                open(file_path, 'rb'),
                content_type=content_type,
                as_attachment=False,  # View inline, not download
                filename=smart_str(project_file.filename)
            )
            return response
        except IOError:
            messages.error(request, "Error reading file from server.")
            return redirect('project_detail', project_id=project_file.project.id)
            
    except ProjectFile.DoesNotExist:
        messages.error(request, "File not found.")
        return redirect('project_list')
    except Exception as e:
        messages.error(request, f"Error viewing file: {str(e)}")
        return redirect('project_list')
    

@login_required
@require_POST
def add_comment_ajax(request, task_id):
    """AJAX view to add comment when status changes to in_progress"""
    try:
        task = get_object_or_404(Task, id=task_id)
        user = request.user
        
        # Check permissions - user must be assigned to task or be admin
        if not user.is_admin() and not task.is_assigned_to_user(user):
            return JsonResponse({'success': False, 'error': 'Permission denied'})
        
        # Parse request data
        data = json.loads(request.body)
        content = data.get('content', '').strip()
        
        if not content:
            return JsonResponse({'success': False, 'error': 'Comment content is required'})
        
        # Create the comment
        comment = Comment.objects.create(
            task=task,
            user=user,
            content=content,
            is_internal=False  # Status change comments are always public
        )
        
        # Create history entry
        TaskHistory.objects.create(
            task=task,
            user=user,
            action='Comment added (status change)',
            new_value=content[:100] + '...' if len(content) > 100 else content
        )
        
        return JsonResponse({
            'success': True, 
            'message': 'Comment added successfully',
            'comment_id': comment.id
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})