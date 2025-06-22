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
from xhtml2pdf import pisa
import json
import csv
from datetime import datetime, timedelta
import openpyxl
import os
import pdfkit
from django.conf import settings
from django.utils import timezone
from django.template.loader import get_template
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from datetime import datetime
from tasks.models import Task
import html
from django.utils.html import strip_tags

from django.contrib.auth.views import (
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView
)
from django.urls import reverse_lazy

import pdfkit
from django.conf import settings
from django.template.loader import render_to_string
from django.http import HttpResponse
import os

from openpyxl.styles import Font, PatternFill, Alignment
from .models import Division
from .forms import DivisionForm
from .models import User, Task, Comment, Division, TaskHistory
from .forms import (
    CustomUserCreationForm, CustomAuthenticationForm, TaskForm, 
    CommentForm, TaskFilterForm, TaskUpdateForm, UserManagementForm
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
    """Main dashboard view"""
    user = request.user
    
    # Get user's tasks
    if user.is_admin():
        # Admins see all tasks in their division
        if user.is_super_admin():
            all_tasks = Task.objects.all()
        else:
            all_tasks = Task.objects.filter(division=user.division)
    else:
        # Regular users see only their assigned tasks
        all_tasks = Task.objects.filter(assigned_to=user)
    
    # Task statistics
    total_tasks = all_tasks.count()
    pending_tasks = all_tasks.filter(status='pending').count()
    in_progress_tasks = all_tasks.filter(status='in_progress').count()
    completed_tasks = all_tasks.filter(status='completed').count()
    overdue_tasks = all_tasks.filter(
        due_date__lt=timezone.now(),
        status__in=['pending', 'in_progress']
    ).count()
    
    # Recent tasks
    recent_tasks = all_tasks.order_by('-created_at')[:5]
    
    # My tasks (for current user)
    my_tasks = Task.objects.filter(assigned_to=user).order_by('-created_at')[:5]
    
    context = {
        'total_tasks': total_tasks,
        'pending_tasks': pending_tasks,
        'in_progress_tasks': in_progress_tasks,
        'completed_tasks': completed_tasks,
        'overdue_tasks': overdue_tasks,
        'recent_tasks': recent_tasks,
        'my_tasks': my_tasks,
    }
    
    return render(request, 'tasks/dashboard.html', context)


@login_required
def task_list(request):
    """Task list view with filtering"""
    user = request.user
    
    # Base queryset
    if user.is_admin():
        if user.is_super_admin():
            tasks = Task.objects.all()
        else:
            tasks = Task.objects.filter(division=user.division)
    else:
        tasks = Task.objects.filter(assigned_to=user)
    
    # Apply filters
    filter_form = TaskFilterForm(request.GET, user=user)
    if filter_form.is_valid():
        if filter_form.cleaned_data['status']:
            tasks = tasks.filter(status=filter_form.cleaned_data['status'])
        if filter_form.cleaned_data['priority']:
            tasks = tasks.filter(priority=filter_form.cleaned_data['priority'])
        if filter_form.cleaned_data['assigned_to']:
            tasks = tasks.filter(assigned_to=filter_form.cleaned_data['assigned_to'])
        if filter_form.cleaned_data['date_from']:
            tasks = tasks.filter(created_at__date__gte=filter_form.cleaned_data['date_from'])
        if filter_form.cleaned_data['date_to']:
            tasks = tasks.filter(created_at__date__lte=filter_form.cleaned_data['date_to'])
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        tasks = tasks.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(assigned_to__username__icontains=search_query) |
            Q(assigned_to__first_name__icontains=search_query) |
            Q(assigned_to__last_name__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(tasks.order_by('-created_at'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'filter_form': filter_form,
        'search_query': search_query,
    }
    
    return render(request, 'tasks/task_list.html', context)


@login_required
def task_detail(request, task_id):
    """Task detail view"""
    task = get_object_or_404(Task, id=task_id)
    user = request.user
    
    # Check permissions
    if not user.is_admin() and task.assigned_to != user:
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
    
    # Task update form for assigned user or admin
    update_form = None
    if user == task.assigned_to or user.is_admin():
        update_form = TaskUpdateForm(instance=task)
    
    context = {
        'task': task,
        'comments': comments,
        'comment_form': comment_form,
        'update_form': update_form,
    }
    
    return render(request, 'tasks/task_detail.html', context)


@login_required
def task_create(request):
    """Create new task"""
    user = request.user
    
    if request.method == 'POST':
        form = TaskForm(request.POST, user=user)
        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = user
            # Set division - if user has no division, use the first available division
            if user.division:
                task.division = user.division
            else:
                # For super admin or users without division, use the first division
                task.division = Division.objects.first()
            task.save()
            
            # Create history entry
            TaskHistory.objects.create(
                task=task,
                user=user,
                action='Task created',
                new_value=f'Task "{task.title}" created'
            )
            
            messages.success(request, 'Task created successfully!')
            return redirect('task_detail', task_id=task.id)
    else:
        form = TaskForm(user=user)
    
    return render(request, 'tasks/task_form.html', {'form': form, 'title': 'Create Task'})


@login_required
def task_edit(request, task_id):
    """Edit existing task"""
    task = get_object_or_404(Task, id=task_id)
    user = request.user
    
    # Check permissions
    if not user.is_admin() and task.created_by != user:
        messages.error(request, 'You do not have permission to edit this task.')
        return redirect('task_detail', task_id=task.id)
    
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task, user=user)
        if form.is_valid():
            old_values = {
                'title': task.title,
                'status': task.status,
                'priority': task.priority,
                'assigned_to': task.assigned_to,
            }
            
            task = form.save()
            
            # Create history entries for changes
            for field, old_value in old_values.items():
                new_value = getattr(task, field)
                if old_value != new_value:
                    TaskHistory.objects.create(
                        task=task,
                        user=user,
                        action=f'{field.replace("_", " ").title()} changed',
                        old_value=str(old_value),
                        new_value=str(new_value)
                    )
            
            messages.success(request, 'Task updated successfully!')
            return redirect('task_detail', task_id=task.id)
    else:
        form = TaskForm(instance=task, user=user)
    
    return render(request, 'tasks/task_form.html', {'form': form, 'title': 'Edit Task', 'task': task})


@login_required
@require_POST
def task_update_status(request, task_id):
    """Update task status via AJAX"""
    task = get_object_or_404(Task, id=task_id)
    user = request.user
    
    # Check permissions
    if not user.is_admin() and task.assigned_to != user:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    try:
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
    if not request.user.is_admin():
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')

    users = User.objects.all()
    if not request.user.is_super_admin():
        users = users.filter(division=request.user.division)

    search_query = request.GET.get('search')
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    paginator = Paginator(users.order_by('username'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ✅ Add admin count and new users this month
    total_users = users.count()
    admin_count = users.filter(role='admin').count()
    active_users_count = users.filter(is_active=True).count()

    now_date = now()
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
    }

    return render(request, 'tasks/user_management.html', context)


@login_required
def user_edit(request, user_id):
    """Edit user view for admins (user info only)"""
    if not request.user.is_admin():
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    user_to_edit = get_object_or_404(User, id=user_id)

    # Admins can only edit users in their own division (unless super admin)
    if not request.user.is_super_admin() and user_to_edit.division != request.user.division:
        messages.error(request, 'You can only edit users in your division.')
        return redirect('user_management')
    
    if request.method == 'POST':
        form = UserManagementForm(request.POST, instance=user_to_edit)
        if form.is_valid():
            form.save()
            messages.success(request, f'User {user_to_edit.username} updated successfully!')
            return redirect('user_management')
    else:
        form = UserManagementForm(instance=user_to_edit)
    
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
    status = request.GET.get('status')
    priority = request.GET.get('priority')
    assigned_to = request.GET.get('assigned_to')
    
    # Base queryset
    tasks = Task.objects.all()
    
    # Apply filters based on user role
    if request.user.role == 'user':
        tasks = tasks.filter(Q(assigned_to=request.user) | Q(created_by=request.user))
    elif request.user.role == 'admin':
        tasks = tasks.filter(division=request.user.division)
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
    
    if status:
        tasks = tasks.filter(status=status)
    
    if priority:
        tasks = tasks.filter(priority=priority)
    
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
    
    # Task distribution by priority
    priority_stats = tasks.values('priority').annotate(
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
    
    context = {
        'tasks': tasks.order_by('-created_at')[:20],  # Latest 20 tasks for preview
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'pending_tasks': pending_tasks,
        'in_progress_tasks': in_progress_tasks,
        'overdue_tasks': overdue_tasks,
        'division_stats': division_stats,
        'priority_stats': priority_stats,
        'status_stats': status_stats,
        'avg_completion_time': avg_completion_time,
        'recent_tasks_count': recent_tasks.count(),
        'divisions': Division.objects.all(),
        'users': User.objects.filter(is_active=True),
        'date_from': date_from,
        'date_to': date_to,
        'selected_division': division_id,
        'selected_status': status,
        'selected_priority': priority,
        'selected_assigned_to': assigned_to,
    }
    
    return render(request, 'tasks/reports.html', context)


@login_required
def export_tasks_excel(request):
    """Export filtered tasks to Excel format with cleaned description."""
    # Get filters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    division_id = request.GET.get('division')
    status = request.GET.get('status')
    priority = request.GET.get('priority')
    assigned_to = request.GET.get('assigned_to')

    # Queryset
    tasks = Task.objects.select_related('assigned_to', 'created_by', 'division').all()

    # Role-based filter
    if request.user.role == 'user':
        tasks = tasks.filter(Q(assigned_to=request.user) | Q(created_by=request.user))
    elif request.user.role == 'admin':
        tasks = tasks.filter(division=request.user.division)

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
    if status:
        tasks = tasks.filter(status=status)
    if priority:
        tasks = tasks.filter(priority=priority)
    if assigned_to:
        tasks = tasks.filter(assigned_to_id=assigned_to)

    # Prepare Excel workbook
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True, 'remove_timezone': True})
    tasks_sheet = workbook.add_worksheet('Tasks')
    summary_sheet = workbook.add_worksheet('Summary')

    # Formats
    header_format = workbook.add_format({'bold': True, 'bg_color': '#4f46e5', 'font_color': 'white', 'border': 1})
    cell_format = workbook.add_format({'border': 1, 'text_wrap': True})
    date_format = workbook.add_format({'border': 1, 'num_format': 'yyyy-mm-dd hh:mm'})

    # Headers
    tasks_headers = [
        'ID', 'Title', 'Description', 'Status', 'Priority', 'Division',
        'Created By', 'Assigned To', 'Created Date', 'Due Date',
        'Completed Date', 'Estimated Hours', 'Actual Hours'
    ]
    for col, header in enumerate(tasks_headers):
        tasks_sheet.write(0, col, header, header_format)

    # Data rows
    for row, task in enumerate(tasks.order_by('-created_at'), 1):
        cleaned_description = html.unescape(strip_tags(task.description or ''))
        tasks_sheet.write(row, 0, task.id, cell_format)
        tasks_sheet.write(row, 1, task.title, cell_format)
        tasks_sheet.write(row, 2, cleaned_description[:500] + '...' if len(cleaned_description) > 500 else cleaned_description, cell_format)
        tasks_sheet.write(row, 3, task.get_status_display(), cell_format)
        tasks_sheet.write(row, 4, task.get_priority_display(), cell_format)
        tasks_sheet.write(row, 5, task.division.name if task.division else 'N/A', cell_format)
        tasks_sheet.write(row, 6, task.created_by.get_full_name() if task.created_by else 'N/A', cell_format)
        tasks_sheet.write(row, 7, task.assigned_to.get_full_name() if task.assigned_to else 'N/A', cell_format)
        tasks_sheet.write(row, 8, task.created_at, date_format)
        tasks_sheet.write(row, 9, task.due_date, date_format)
        tasks_sheet.write(row, 10, task.completed_at if task.completed_at else 'N/A', date_format)
        tasks_sheet.write(row, 11, task.estimated_hours if task.estimated_hours else 'N/A', cell_format)
        tasks_sheet.write(row, 12, task.actual_hours if task.actual_hours else 'N/A', cell_format)

    # Column widths
    tasks_sheet.set_column('A:A', 8)
    tasks_sheet.set_column('B:B', 30)
    tasks_sheet.set_column('C:C', 50)
    tasks_sheet.set_column('D:D', 12)
    tasks_sheet.set_column('E:E', 10)
    tasks_sheet.set_column('F:F', 15)
    tasks_sheet.set_column('G:G', 20)
    tasks_sheet.set_column('H:H', 20)
    tasks_sheet.set_column('I:M', 18)

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


from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

@csrf_exempt  # Optional: only if you aren’t using CSRF token via JS
@require_POST
@login_required
def toggle_user_status(request, user_id):
    if not request.user.is_admin():
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)

    user = get_object_or_404(User, id=user_id)

    if user == request.user:
        return JsonResponse({'success': False, 'message': 'You cannot deactivate yourself.'}, status=400)

    user.is_active = not user.is_active
    user.save()

    return JsonResponse({
        'success': True,
        'new_status': user.is_active,
        'message': f'User {user.username} is now {"active" if user.is_active else "inactive"}'
    })




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
    # Extract filters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    division_id = request.GET.get('division')
    status = request.GET.get('status')
    priority = request.GET.get('priority')
    assigned_to = request.GET.get('assigned_to')

    # Base queryset
    tasks_qs = Task.objects.select_related('assigned_to', 'created_by', 'division').all()

    # Role-based filtering
    if request.user.role == 'user':
        tasks_qs = tasks_qs.filter(Q(assigned_to=request.user) | Q(created_by=request.user))
    elif request.user.role == 'admin':
        tasks_qs = tasks_qs.filter(division=request.user.division)

    # Apply filters
    try:
        if date_from:
            tasks_qs = tasks_qs.filter(created_at__date__gte=datetime.strptime(date_from, '%Y-%m-%d').date())
        if date_to:
            tasks_qs = tasks_qs.filter(created_at__date__lte=datetime.strptime(date_to, '%Y-%m-%d').date())
    except ValueError:
        pass

    if division_id:
        tasks_qs = tasks_qs.filter(division_id=division_id)
    if status:
        tasks_qs = tasks_qs.filter(status=status)
    if priority:
        tasks_qs = tasks_qs.filter(priority=priority)
    if assigned_to:
        tasks_qs = tasks_qs.filter(assigned_to_id=assigned_to)

    # Convert queryset to list AFTER filtering
    tasks = list(tasks_qs.order_by('-created_at'))

    # Clean HTML tags/entities from description
    for task in tasks:
        task.description_clean = html.unescape(strip_tags(task.description or ''))

    # Get division information for the template
    divisions = Division.objects.all()
    selected_division_obj = None
    
    if division_id:
        try:
            selected_division_obj = Division.objects.get(id=division_id)
        except Division.DoesNotExist:
            selected_division_obj = None

    # Prepare logo path
    logo_path = os.path.abspath(os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png'))

    # Render HTML template
    template = get_template('tasks/pdf_template.html')
    rendered_html = template.render({
        'tasks': tasks,
        'generated_at': timezone.now(),
        'logo_path': f'file:///{logo_path.replace(os.sep, "/")}',
        'user': request.user,
        'divisions': divisions,
        'selected_division': division_id,  # Pass the division ID as string
        'selected_division_obj': selected_division_obj,  # Pass the actual division object
        'date_from': date_from,
        'date_to': date_to,
        'selected_status': status,
        'selected_priority': priority,
        'selected_assigned_to': assigned_to,
    })

    # PDF options and configuration
    options = {
        'enable-local-file-access': None,
        'encoding': 'UTF-8',
        'quiet': ''
    }
    config = pdfkit.configuration(wkhtmltopdf=settings.WKHTMLTOPDF_PATH)

    # Generate PDF
    pdf = pdfkit.from_string(rendered_html, False, options=options, configuration=config)

    # Return response
    response = HttpResponse(pdf, content_type='application/pdf')
    filename = f'tasks_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

from django.views.decorators.http import require_http_methods

@login_required
def delete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)

    if not request.user.is_admin() and task.created_by != request.user:
        messages.error(request, 'You do not have permission to delete this task.')
        return redirect('task_detail', task_id=task.id)

    task.delete()
    messages.success(request, 'Task deleted successfully.')
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


