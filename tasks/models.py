from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from django.db.models import Count, Q
import os
from datetime import timedelta
from tinymce.models import HTMLField


# ----------------------------
# Division and Custom User
# ----------------------------
class Division(models.Model):
    """Model for organizational divisions"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    code = models.CharField(max_length=20, blank=True, help_text="Unique division code (optional)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        # FIXED: Only show code if it exists and is not empty
        if self.code and self.code.strip():
            return f"{self.name} ({self.code})"
        return self.name

    def get_display_code(self):
        """Get code for display purposes - use name if code is empty"""
        if self.code and self.code.strip():
            return self.code.strip().upper()
        return self.name[:4].upper().replace(' ', '')

    def save(self, *args, **kwargs):
        """Auto-generate code if not provided"""
        if not self.code or not self.code.strip():
            # Generate code from division name if not provided
            base_code = self.name[:4].upper().replace(' ', '')
            counter = 1
            final_code = base_code
            
            # Ensure uniqueness
            while Division.objects.filter(code=final_code).exclude(pk=self.pk).exists():
                final_code = f"{base_code}{counter}"
                counter += 1
            
            self.code = final_code
        
        super().save(*args, **kwargs)

    def get_user_count(self):
        """Get total number of users in this division"""
        return self.user_set.filter(is_active=True).count()

    def get_admin_count(self):
        """Get number of admins in this division"""
        return self.user_set.filter(role__in=['admin', 'super_admin'], is_active=True).count()

    def get_project_count(self):
        """Get number of projects in this division"""
        return self.project_set.count()

    def get_active_task_count(self):
        """Get number of active tasks in this division"""
        return Task.objects.filter(
            division=self,
            status__in=['pending', 'in_progress']
        ).count()

    class Meta:
        ordering = ['name']
        verbose_name_plural = "Divisions"

class User(AbstractUser):
    """Custom user model with division and role management"""
    ROLE_CHOICES = [
        ('user', 'User'),
        ('admin', 'Admin'),
        ('super_admin', 'Super Admin'),
    ]

    division = models.ForeignKey(Division, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    phone = models.CharField(max_length=20, blank=True)
    profile_picture = models.ImageField(
        upload_to='profiles/', 
        blank=True, 
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])]
    )
    employee_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    is_active = models.BooleanField(default=False)  # Requires admin approval
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} ({self.get_full_name()})"

    def is_admin(self):
        """Check if user is admin or super_admin"""
        return self.role in ['admin', 'super_admin']

    def is_super_admin(self):
        """Check if user is super admin"""
        return self.role == 'super_admin'

    def get_display_name(self):
        """Get user's display name (full name or username)"""
        return self.get_full_name() or self.username

    def get_my_projects(self):
        """Get projects where user has assigned tasks"""
        return Project.objects.filter(tasks__assigned_to=self).distinct()

    def get_managed_projects(self):
        """Get projects managed by this admin"""
        if self.is_admin():
            return Project.objects.filter(assigned_to_admin=self)
        return Project.objects.none()

    def get_workload_stats(self):
        """Get user's current workload statistics"""
        my_tasks = self.assigned_tasks.exclude(status__in=['completed', 'cancelled'])
        now = timezone.now()
        
        return {
            'total_active_tasks': my_tasks.count(),
            'high_priority_tasks': my_tasks.filter(priority__in=['high', 'urgent']).count(),
            'overdue_tasks': my_tasks.filter(
                due_date__lt=now,
                status__in=['pending', 'in_progress']
            ).count(),
            'due_this_week': my_tasks.filter(
                due_date__gte=now,
                due_date__lte=now + timedelta(days=7),
                status__in=['pending', 'in_progress']
            ).count(),
            'projects_count': self.get_my_projects().count(),
            'collaborative_tasks': my_tasks.annotate(
                assignee_count=Count('assigned_to')
            ).filter(assignee_count__gt=1).count(),
        }

    def get_completion_rate(self, days=30):
        """Get task completion rate for the last N days"""
        from django.utils import timezone
        from datetime import timedelta
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        tasks_in_period = self.assigned_tasks.filter(created_at__range=[start_date, end_date])
        total_tasks = tasks_in_period.count()
        
        if total_tasks == 0:
            return 0
        
        completed_tasks = tasks_in_period.filter(status='completed').count()
        return round((completed_tasks / total_tasks) * 100, 1)

    class Meta:
        ordering = ['username']
        indexes = [
            models.Index(fields=['role', 'is_active']),
            models.Index(fields=['division', 'role']),
        ]


# ----------------------------
# Project and Project Files
# ----------------------------

class Project(models.Model):
    """Model for projects with admin assignment and file management"""
    STATUS_CHOICES = [
        ('planning', 'Planning'),
        ('active', 'Active'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    title = models.CharField(max_length=255)
    description = HTMLField(
        blank=True, 
        null=True,
        help_text="Detailed project description with rich formatting"
    )
    code = models.CharField(max_length=20, blank=True, help_text="Unique project code (auto-generated)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_projects")
    assigned_to_admin = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="managed_projects",
        limit_choices_to={'role__in': ['admin', 'super_admin']},
        help_text="Admin responsible for this project"
    )
    division = models.ForeignKey(Division, on_delete=models.SET_NULL, null=True, help_text="Division this project belongs to")
    
    # Project timeline
    start_date = models.DateField(null=True, blank=True, help_text="Project start date")
    end_date = models.DateField(null=True, blank=True, help_text="Project target completion date")
    
    # Budget and resource tracking
    estimated_budget = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Estimated budget for the project"
    )
    actual_budget = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Actual budget spent"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        # FIXED: Only show code if it exists and is not empty
        if self.code and self.code.strip():
            return f"{self.code} - {self.title}"
        return self.title

    def save(self, *args, **kwargs):
        if not self.code:
            # Auto-generate project code if not provided
            self.code = self.generate_project_code()
        super().save(*args, **kwargs)

    def generate_project_code(self):
        """Generate unique project code"""
        import uuid
        
        # Use division's display code or fallback to "GEN"
        if self.division:
            division_code = self.division.get_display_code()
        else:
            division_code = "GEN"
        
        year = timezone.now().year
        random_part = str(uuid.uuid4())[:6].upper()
        
        # Ensure uniqueness
        base_code = f"{division_code}-{year}-{random_part}"
        counter = 1
        final_code = base_code
        
        # Check if code already exists and make it unique
        while Project.objects.filter(code=final_code).exclude(pk=self.pk if self.pk else None).exists():
            final_code = f"{base_code}-{counter}"
            counter += 1
            
        return final_code

    # ... rest of your methods remain exactly the same ...
    def get_task_count(self):
        """Get total number of tasks in this project"""
        return self.tasks.count()

    def get_completed_task_count(self):
        """Get number of completed tasks in this project"""
        return self.tasks.filter(status='completed').count()

    def get_active_tasks_count(self):
        """Get count of non-completed tasks"""
        return self.tasks.exclude(status__in=['completed', 'cancelled']).count()

    def get_overdue_tasks_count(self):
        """Get count of overdue tasks"""
        return self.tasks.filter(
            due_date__lt=timezone.now(),
            status__in=['pending', 'in_progress']
        ).count()

    def get_progress_percentage(self):
        """Get project completion percentage"""
        total = self.get_task_count()
        if total == 0:
            return 0
        completed = self.get_completed_task_count()
        return round((completed / total) * 100, 1)

    def get_team_members(self):
        """Get all unique users who have tasks in this project"""
        return User.objects.filter(assigned_tasks__project=self).distinct()

    def get_team_size(self):
        """Get number of team members"""
        return self.get_team_members().count()

    def is_overdue(self):
        """Check if project is overdue"""
        if self.end_date:
            return timezone.now().date() > self.end_date and self.status != 'completed'
        return False

    def get_days_remaining(self):
        """Get number of days remaining until end date"""
        if not self.end_date:
            return None
        
        delta = self.end_date - timezone.now().date()
        return delta.days

    def get_recent_activity(self, days=7):
        """Get recent task activities in this project"""
        recent_date = timezone.now() - timedelta(days=days)
        return TaskHistory.objects.filter(
            task__project=self,
            timestamp__gte=recent_date
        ).select_related('user', 'task').order_by('-timestamp')[:10]

    def get_budget_utilization(self):
        """Get budget utilization percentage"""
        if not self.estimated_budget or self.estimated_budget == 0:
            return 0
        
        if not self.actual_budget:
            return 0
            
        return round((self.actual_budget / self.estimated_budget) * 100, 1)

    def get_status_badge_class(self):
        """Get CSS class for status badge"""
        status_classes = {
            'planning': 'bg-info',
            'active': 'bg-success',
            'on_hold': 'bg-warning',
            'completed': 'bg-primary',
            'cancelled': 'bg-secondary'
        }
        return status_classes.get(self.status, 'bg-secondary')

    def get_priority_badge_class(self):
        """Get CSS class for priority badge"""
        priority_classes = {
            'low': 'bg-success',
            'medium': 'bg-warning',
            'high': 'bg-danger',
            'critical': 'bg-dark'
        }
        return priority_classes.get(self.priority, 'bg-secondary')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['division', 'assigned_to_admin']),
            models.Index(fields=['start_date', 'end_date']),
        ]
        
class ProjectFile(models.Model):
    """Model for project file attachments"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(
        upload_to='project_files/',
        validators=[FileExtensionValidator(
            allowed_extensions=['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 
                              'txt', 'csv', 'png', 'jpg', 'jpeg', 'gif', 'zip', 'rar']
        )]
    )
    filename = models.CharField(max_length=255, blank=True)
    file_size = models.BigIntegerField(blank=True, null=True)
    file_type = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True, help_text="Brief description of the file")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_public = models.BooleanField(default=True, help_text="Whether file is visible to all project members")

    def __str__(self):
        return self.filename or self.file.name

    def save(self, *args, **kwargs):
        if not self.filename:
            self.filename = os.path.basename(self.file.name)
        if not self.file_size and self.file:
            self.file_size = self.file.size
        if not self.file_type and self.file:
            self.file_type = os.path.splitext(self.filename)[1][1:].lower()
        super().save(*args, **kwargs)

    def get_file_size_display(self):
        """Get human-readable file size"""
        if not self.file_size:
            return "Unknown"
        
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def get_file_icon_class(self):
        """Get CSS icon class based on file type"""
        icon_map = {
            'pdf': 'fas fa-file-pdf text-danger',
            'doc': 'fas fa-file-word text-primary',
            'docx': 'fas fa-file-word text-primary',
            'xls': 'fas fa-file-excel text-success',
            'xlsx': 'fas fa-file-excel text-success',
            'ppt': 'fas fa-file-powerpoint text-warning',
            'pptx': 'fas fa-file-powerpoint text-warning',
            'png': 'fas fa-file-image text-info',
            'jpg': 'fas fa-file-image text-info',
            'jpeg': 'fas fa-file-image text-info',
            'gif': 'fas fa-file-image text-info',
            'zip': 'fas fa-file-archive text-secondary',
            'rar': 'fas fa-file-archive text-secondary',
            'txt': 'fas fa-file-alt text-muted',
            'csv': 'fas fa-file-csv text-success',
        }
        return icon_map.get(self.file_type, 'fas fa-file text-muted')

    class Meta:
        ordering = ['-uploaded_at']


# ----------------------------
# Project Team Membership (Optional - for better team management)
# ----------------------------

class ProjectMember(models.Model):
    """Explicit project membership for better team management"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='project_memberships')
    role = models.CharField(
        max_length=20,
        choices=[
            ('member', 'Team Member'),
            ('lead', 'Team Lead'),
            ('collaborator', 'Collaborator'),
            ('observer', 'Observer'),
        ],
        default='member'
    )
    permissions = models.JSONField(
        default=dict,
        help_text="Custom permissions for this member in JSON format"
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ['project', 'user']
        ordering = ['-joined_at']

    def __str__(self):
        return f"{self.user.get_display_name()} - {self.project.title} ({self.role})"


# ----------------------------
# Task, History, Attachments, Comments
# ----------------------------

class Task(models.Model):
    """Model for tasks with multiple assignees support"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('review', 'Under Review'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('blocked', 'Blocked'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    title = models.CharField(max_length=200)
    description = HTMLField(
        help_text="Task description with formatting options",
        default=''
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    
    # Relationships
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_tasks')
    assigned_to = models.ManyToManyField(User, related_name='assigned_tasks', blank=True)
    division = models.ForeignKey(Division, on_delete=models.CASCADE)
    
    # Task dependencies
    depends_on = models.ManyToManyField(
        'self', 
        symmetrical=False, 
        blank=True, 
        related_name='dependent_tasks',
        help_text="Tasks that must be completed before this task can start"
    )
    
    # Time tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    due_date = models.DateTimeField(null=True, blank=True)
    start_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Effort estimation
    estimated_hours = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)]
    )
    actual_hours = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)]
    )
    
    # Progress tracking
    progress_percentage = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Manual progress percentage (0-100)"
    )
    
    # Additional metadata
    tags = models.CharField(max_length=255, blank=True, help_text="Comma-separated tags")
    is_template = models.BooleanField(default=False, help_text="Use this task as a template")

    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        # Auto-set completed_at when status changes to completed
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
            self.progress_percentage = 100
        elif self.status != 'completed':
            self.completed_at = None
            if self.progress_percentage == 100:
                self.progress_percentage = 0
        super().save(*args, **kwargs)

    def get_assignees_display(self):
        """Get a string of all assigned users"""
        assignees = self.assigned_to.all()
        if not assignees.exists():
            return "No assignees"
        
        if assignees.count() <= 2:
            return ", ".join([user.get_display_name() for user in assignees])
        else:
            first_two = list(assignees[:2])
            names = [user.get_display_name() for user in first_two]
            remaining = assignees.count() - 2
            return f"{', '.join(names)} +{remaining} more"

    def is_assigned_to_user(self, user):
        """Check if a specific user is assigned to this task"""
        return self.assigned_to.filter(id=user.id).exists()

    def get_assignee_count(self):
        """Get the number of assigned users"""
        return self.assigned_to.count()

    def is_collaborative(self):
        """Check if this is a collaborative task (multiple assignees)"""
        return self.assigned_to.count() > 1

    def get_collaboration_level(self):
        """Get collaboration level description"""
        count = self.assigned_to.count()
        if count == 1:
            return "Individual Task"
        elif count <= 3:
            return "Small Team"
        elif count <= 6:
            return "Medium Team"
        else:
            return "Large Team"

    def get_assignee_avatars_html(self):
        """Get HTML for displaying assignee avatars"""
        assignees = self.assigned_to.all()[:3]  # Show max 3 avatars
        html_parts = []
        
        for user in assignees:
            initial = user.get_display_name()[0].upper()
            html_parts.append(f'<span class="user-avatar" title="{user.get_display_name()}">{initial}</span>')
        
        if self.assigned_to.count() > 3:
            remaining = self.assigned_to.count() - 3
            html_parts.append(f'<span class="user-avatar-more">+{remaining}</span>')
        
        return ''.join(html_parts)

    def is_overdue(self):
        """Check if task is overdue"""
        if self.due_date and self.status not in ['completed', 'cancelled']:
            return timezone.now() > self.due_date
        return False

    def get_days_until_due(self):
        """Get number of days until due date"""
        if not self.due_date:
            return None
        
        delta = self.due_date.date() - timezone.now().date()
        return delta.days

    def can_start(self):
        """Check if task can start (all dependencies completed)"""
        if not self.depends_on.exists():
            return True
        return not self.depends_on.exclude(status='completed').exists()

    def get_blocking_dependencies(self):
        """Get list of incomplete dependencies"""
        return self.depends_on.exclude(status='completed')

    def get_dependent_tasks(self):
        """Get tasks that depend on this task"""
        return self.dependent_tasks.exclude(status__in=['completed', 'cancelled'])

    def get_effort_variance(self):
        """Get variance between estimated and actual hours"""
        if not self.estimated_hours or not self.actual_hours:
            return None
        return self.actual_hours - self.estimated_hours

    def get_effort_variance_percentage(self):
        """Get effort variance as percentage"""
        if not self.estimated_hours or self.estimated_hours == 0:
            return None
        
        variance = self.get_effort_variance()
        if variance is None:
            return None
            
        return round((variance / self.estimated_hours) * 100, 1)

    def get_tag_list(self):
        """Get tags as a list"""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]

    def can_user_edit(self, user):
        """Check if user can edit this task"""
        return (
            user.is_admin() or 
            self.created_by == user or 
            self.is_assigned_to_user(user)
        )

    def get_priority_badge_class(self):
        """Get CSS class for priority badge"""
        priority_classes = {
            'low': 'bg-success',
            'medium': 'bg-warning',
            'high': 'bg-danger',
            'urgent': 'bg-dark'
        }
        return priority_classes.get(self.priority, 'bg-secondary')

    def get_status_badge_class(self):
        """Get CSS class for status badge"""
        status_classes = {
            'pending': 'bg-warning',
            'in_progress': 'bg-info',
            'review': 'bg-purple',
            'completed': 'bg-success',
            'cancelled': 'bg-secondary',
            'blocked': 'bg-danger'
        }
        return status_classes.get(self.status, 'bg-secondary')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['project', 'status']),
            models.Index(fields=['division', 'status']),
            models.Index(fields=['due_date', 'status']),
        ]


class TaskAttachment(models.Model):
    """Model for task file attachments"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(
        upload_to='task_attachments/',
        validators=[FileExtensionValidator(
            allowed_extensions=['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 
                              'txt', 'csv', 'png', 'jpg', 'jpeg', 'gif', 'zip', 'rar']
        )]
    )
    filename = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_size = models.PositiveIntegerField()  # in bytes
    file_type = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.filename} - {self.task.title}"

    def save(self, *args, **kwargs):
        if not self.file_type and self.filename:
            self.file_type = os.path.splitext(self.filename)[1][1:].lower()
        super().save(*args, **kwargs)

    def get_file_size_display(self):
        """Get human-readable file size"""
        size = self.file_size
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"

    def get_file_icon_class(self):
        """Get CSS icon class based on file type"""
        icon_map = {
            'pdf': 'fas fa-file-pdf text-danger',
            'doc': 'fas fa-file-word text-primary',
            'docx': 'fas fa-file-word text-primary',
            'xls': 'fas fa-file-excel text-success',
            'xlsx': 'fas fa-file-excel text-success',
            'ppt': 'fas fa-file-powerpoint text-warning',
            'pptx': 'fas fa-file-powerpoint text-warning',
            'png': 'fas fa-file-image text-info',
            'jpg': 'fas fa-file-image text-info',
            'jpeg': 'fas fa-file-image text-info',
            'gif': 'fas fa-file-image text-info',
            'zip': 'fas fa-file-archive text-secondary',
            'rar': 'fas fa-file-archive text-secondary',
            'txt': 'fas fa-file-alt text-muted',
            'csv': 'fas fa-file-csv text-success',
        }
        return icon_map.get(self.file_type, 'fas fa-file text-muted')

    class Meta:
        ordering = ['-uploaded_at']


class TaskHistory(models.Model):
    """Model to track task changes"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='history')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=100)  # e.g., "Status changed", "Assigned to user"
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    field_changed = models.CharField(max_length=50, blank=True)  # Which field was changed
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self):
        return f"{self.action} - {self.task.title}"

    def get_change_summary(self):
        """Get a human-readable summary of the change"""
        if self.old_value and self.new_value:
            return f"{self.action}: {self.old_value} → {self.new_value}"
        elif self.new_value:
            return f"{self.action}: {self.new_value}"
        else:
            return self.action

    def get_action_icon(self):
        """Get icon for the action type"""
        icon_map = {
            'created': 'fas fa-plus-circle text-success',
            'status': 'fas fa-exchange-alt text-info',
            'assigned': 'fas fa-user-plus text-primary',
            'comment': 'fas fa-comment text-secondary',
            'file': 'fas fa-file text-warning',
            'priority': 'fas fa-exclamation-triangle text-danger',
            'due_date': 'fas fa-calendar text-info',
            'completed': 'fas fa-check-circle text-success',
            'deleted': 'fas fa-trash text-danger',
        }
        
        action_lower = self.action.lower()
        for key, icon in icon_map.items():
            if key in action_lower:
                return icon
        return 'fas fa-history text-muted'

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "Task histories"
        indexes = [
            models.Index(fields=['task', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
        ]


class Comment(models.Model):
    """Model for task comments"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_internal = models.BooleanField(
        default=False,
        help_text="Internal comments are only visible to admins"
    )
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='replies',
        help_text="Reply to another comment"
    )
    is_pinned = models.BooleanField(default=False, help_text="Pin important comments")
    mention_users = models.ManyToManyField(
        User, 
        blank=True, 
        related_name='mentioned_in_comments',
        help_text="Users mentioned in this comment"
    )

    def __str__(self):
        return f"Comment by {self.user.username} on {self.task.title}"

    def get_content_preview(self, max_length=100):
        """Get a preview of the comment content"""
        if len(self.content) <= max_length:
            return self.content
        return f"{self.content[:max_length]}..."

    def is_edited(self):
        """Check if comment was edited"""
        return self.updated_at > self.created_at

    def get_replies_count(self):
        """Get number of replies to this comment"""
        return self.replies.count()

    def is_reply(self):
        """Check if this is a reply to another comment"""
        return self.parent is not None

    class Meta:
        ordering = ['-is_pinned', '-created_at']
        indexes = [
            models.Index(fields=['task', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]


# ----------------------------
# Notification System
# ----------------------------

class Notification(models.Model):
    """Simple notification system for task and project updates"""
    NOTIFICATION_TYPES = [
        ('task_assigned', 'Task Assigned'),
        ('task_completed', 'Task Completed'),
        ('task_overdue', 'Task Overdue'),
        ('task_comment', 'Task Comment'),
        ('project_assigned', 'Project Assigned'),
        ('project_update', 'Project Update'),
        ('file_uploaded', 'File Uploaded'),
        ('mention', 'Mentioned in Comment'),
        ('deadline_reminder', 'Deadline Reminder'),
        ('system', 'System Notification'),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    
    # Generic foreign key for related objects
    related_object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object_type = models.CharField(max_length=50, null=True, blank=True)  # 'task', 'project', etc.
    
    is_read = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False, help_text="Whether notification was sent via email")
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} - {self.recipient.username}"

    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    def get_related_object(self):
        """Get the related object (task, project, etc.)"""
        if not self.related_object_type or not self.related_object_id:
            return None
        
        model_map = {
            'task': Task,
            'project': Project,
            'comment': Comment,
        }
        
        model_class = model_map.get(self.related_object_type)
        if model_class:
            try:
                return model_class.objects.get(id=self.related_object_id)
            except model_class.DoesNotExist:
                return None
        return None

    def get_notification_icon(self):
        """Get icon class for notification type"""
        icon_map = {
            'task_assigned': 'fas fa-user-plus text-primary',
            'task_completed': 'fas fa-check-circle text-success',
            'task_overdue': 'fas fa-exclamation-triangle text-danger',
            'task_comment': 'fas fa-comment text-info',
            'project_assigned': 'fas fa-project-diagram text-primary',
            'project_update': 'fas fa-sync text-info',
            'file_uploaded': 'fas fa-file-upload text-warning',
            'mention': 'fas fa-at text-purple',
            'deadline_reminder': 'fas fa-clock text-warning',
            'system': 'fas fa-cog text-muted',
        }
        return icon_map.get(self.notification_type, 'fas fa-bell text-muted')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['created_at', 'is_read']),
        ]


# ----------------------------
# Activity Log for Better Tracking
# ----------------------------

class ActivityLog(models.Model):
    """System-wide activity logging"""
    ACTION_TYPES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('view', 'View'),
        ('download', 'Download'),
        ('upload', 'Upload'),
        ('assign', 'Assign'),
        ('complete', 'Complete'),
        ('comment', 'Comment'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    description = models.TextField()
    object_type = models.CharField(max_length=50)  # 'task', 'project', 'user'
    object_id = models.PositiveIntegerField()
    object_name = models.CharField(max_length=255, blank=True)  # For easier searching
    
    # Request metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    
    # Additional context
    extra_data = models.JSONField(default=dict, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} {self.action} {self.object_type} {self.object_name}"

    def get_action_icon(self):
        """Get icon for action type"""
        icon_map = {
            'create': 'fas fa-plus text-success',
            'update': 'fas fa-edit text-info',
            'delete': 'fas fa-trash text-danger',
            'login': 'fas fa-sign-in-alt text-success',
            'logout': 'fas fa-sign-out-alt text-muted',
            'view': 'fas fa-eye text-info',
            'download': 'fas fa-download text-primary',
            'upload': 'fas fa-upload text-warning',
            'assign': 'fas fa-user-plus text-primary',
            'complete': 'fas fa-check-circle text-success',
            'comment': 'fas fa-comment text-secondary',
        }
        return icon_map.get(self.action, 'fas fa-history text-muted')

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['object_type', 'object_id']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
        ]


# ----------------------------
# Task Templates for Reusability
# ----------------------------

class TaskTemplate(models.Model):
    """Template for creating standardized tasks"""
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=100, blank=True)
    
    # Default values for new tasks
    default_priority = models.CharField(max_length=20, choices=Task.PRIORITY_CHOICES, default='medium')
    default_estimated_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    default_tags = models.CharField(max_length=255, blank=True)
    
    # Template metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    division = models.ForeignKey(Division, on_delete=models.CASCADE, null=True, blank=True)
    is_public = models.BooleanField(default=False, help_text="Available to all divisions")
    usage_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def increment_usage(self):
        """Increment usage counter"""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])

    def create_task_from_template(self, project=None, assigned_to=None, created_by=None):
        """Create a new task from this template"""
        task = Task(
            title=self.name,
            description=self.description,
            priority=self.default_priority,
            estimated_hours=self.default_estimated_hours,
            tags=self.default_tags,
            project=project,
            created_by=created_by,
            division=project.division if project else self.division,
        )
        task.save()
        
        if assigned_to:
            if isinstance(assigned_to, list):
                task.assigned_to.set(assigned_to)
            else:
                task.assigned_to.add(assigned_to)
        
        self.increment_usage()
        return task

    class Meta:
        ordering = ['-usage_count', 'name']


# ----------------------------
# Time Tracking for Tasks
# ----------------------------

class TimeEntry(models.Model):
    """Time tracking entries for tasks"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='time_entries')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='time_entries')
    description = models.TextField(blank=True, help_text="What was worked on")
    
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    
    is_billable = models.BooleanField(default=True)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.task.title} ({self.get_duration_display()})"

    def save(self, *args, **kwargs):
        if self.start_time and self.end_time and not self.duration_minutes:
            delta = self.end_time - self.start_time
            self.duration_minutes = int(delta.total_seconds() / 60)
        super().save(*args, **kwargs)

    def get_duration_display(self):
        """Get human-readable duration"""
        if not self.duration_minutes:
            return "In progress"
        
        hours = self.duration_minutes // 60
        minutes = self.duration_minutes % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

    def get_duration_hours(self):
        """Get duration in hours as decimal"""
        if not self.duration_minutes:
            return 0
        return round(self.duration_minutes / 60, 2)

    def get_billable_amount(self):
        """Calculate billable amount"""
        if not self.is_billable or not self.hourly_rate:
            return 0
        return self.get_duration_hours() * self.hourly_rate

    class Meta:
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['task', 'user']),
            models.Index(fields=['start_time', 'end_time']),
        ]


# ----------------------------
# Helper Functions for Dashboard Stats
# ----------------------------

def get_dashboard_stats(user):
    """Get comprehensive dashboard statistics for a user"""
    from django.db.models import Count, Sum, Avg, Q
    from django.utils import timezone
    from datetime import timedelta
    
    now = timezone.now()
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)
    
    # Base task querysets
    if user.is_super_admin():
        all_tasks = Task.objects.all()
        all_projects = Project.objects.all()
    elif user.is_admin():
        all_tasks = Task.objects.filter(division=user.division)
        all_projects = Project.objects.filter(division=user.division)
    else:
        all_tasks = user.assigned_tasks.all()
        all_projects = user.get_my_projects()

    my_tasks = user.assigned_tasks.all()
    
    stats = {
        'my_tasks': {
            'total': my_tasks.count(),
            'pending': my_tasks.filter(status='pending').count(),
            'in_progress': my_tasks.filter(status='in_progress').count(),
            'completed_this_week': my_tasks.filter(
                status='completed',
                completed_at__gte=week_start
            ).count(),
            'overdue': my_tasks.filter(
                due_date__lt=now,
                status__in=['pending', 'in_progress']
            ).count(),
            'due_this_week': my_tasks.filter(
                due_date__gte=now,
                due_date__lte=now + timedelta(days=7),
                status__in=['pending', 'in_progress']
            ).count(),
        },
        'projects': {
            'total': all_projects.count(),
            'my_projects': user.get_my_projects().count(),
            'managed': user.get_managed_projects().count() if user.is_admin() else 0,
            'active': all_projects.filter(status='active').count(),
        },
        'collaboration': {
            'collaborative_tasks': my_tasks.annotate(
                assignee_count=Count('assigned_to')
            ).filter(assignee_count__gt=1).count(),
            'team_members': User.objects.filter(
                assigned_tasks__in=my_tasks
            ).exclude(id=user.id).distinct().count(),
        },
        'productivity': {
            'completion_rate': user.get_completion_rate(30),
            'avg_task_duration': my_tasks.filter(
                status='completed',
                actual_hours__isnull=False
            ).aggregate(avg=Avg('actual_hours'))['avg'] or 0,
        }
    }
    
    # Admin-specific stats
    if user.is_admin():
        stats['admin'] = {
            'total_tasks': all_tasks.count(),
            'total_projects': all_projects.count(),
            'pending_approvals': User.objects.filter(
                is_active=False,
                division=user.division if not user.is_super_admin() else None
            ).count(),
            'overdue_tasks': all_tasks.filter(
                due_date__lt=now,
                status__in=['pending', 'in_progress']
            ).count(),
        }
    
    return stats


def get_user_permissions_for_project(user, project):
    """Get comprehensive user permissions for a project"""
    permissions = {
        'can_view': False,
        'can_edit': False,
        'can_delete': False,
        'can_create_tasks': False,
        'can_manage_files': False,
        'can_manage_members': False,
        'can_view_reports': False,
        'can_manage_budget': False,
    }
    
    if user.is_super_admin():
        # Super admin has all permissions
        for key in permissions:
            permissions[key] = True
    elif user.is_admin():
        if project.assigned_to_admin == user:
            # Project admin has most permissions
            permissions.update({
                'can_view': True,
                'can_edit': True,
                'can_create_tasks': True,
                'can_manage_files': True,
                'can_manage_members': True,
                'can_view_reports': True,
                'can_manage_budget': True,
            })
        elif project.division == user.division:
            # Division admin has limited permissions
            permissions.update({
                'can_view': True,
                'can_create_tasks': True,
                'can_view_reports': True,
            })
    else:
        # Regular user - check if they have tasks in project
        if project.tasks.filter(assigned_to=user).exists():
            permissions.update({
                'can_view': True,
                'can_create_tasks': True,  # For collaboration
            })
    
    return permissions