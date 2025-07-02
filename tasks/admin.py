from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, Division, Task, Comment, TaskAttachment, TaskHistory, Project, ProjectFile


@admin.register(Division)
class DivisionAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name', 'description']
    list_filter = ['created_at']
    ordering = ['name']


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'division', 'role', 'is_active']
    list_filter = ['role', 'division', 'is_active', 'is_staff', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['username']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('division', 'role', 'phone', 'profile_picture')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('division', 'role', 'phone', 'profile_picture')
        }),
    )


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ['created_at', 'updated_at']


class TaskAttachmentInline(admin.TabularInline):
    model = TaskAttachment
    extra = 0
    readonly_fields = ['uploaded_at', 'file_size']


class TaskHistoryInline(admin.TabularInline):
    model = TaskHistory
    extra = 0
    readonly_fields = ['timestamp']


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    # FIXED: Removed 'assigned_to' from list_display and added custom method
    list_display = [
        'title', 'status', 'priority', 'get_assignees_display', 'division', 
        'created_by', 'due_date', 'is_overdue_display', 'created_at'
    ]
    list_filter = [
        'status', 'priority', 'division', 'created_at', 'due_date'
    ]
    # FIXED: Updated search to work with M2M field
    search_fields = ['title', 'description', 'assigned_to__username', 'created_by__username']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'status', 'priority')
        }),
        ('Assignment', {
            'fields': ('created_by', 'assigned_to', 'division', 'project')
        }),
        ('Dates', {
            'fields': ('due_date', 'completed_at')
        }),
        ('Time Tracking', {
            'fields': ('estimated_hours', 'actual_hours')
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    # ADDED: Better widget for many-to-many field
    filter_horizontal = ['assigned_to']
    
    inlines = [CommentInline, TaskAttachmentInline, TaskHistoryInline]
    
    # ADDED: Custom method to display multiple assignees
    def get_assignees_display(self, obj):
        """Display all assigned users in a readable format"""
        assignees = obj.assigned_to.all()
        if not assignees.exists():
            return format_html('<span style="color: #999; font-style: italic;">No assignees</span>')
        
        if assignees.count() <= 2:
            # Show all names if 2 or fewer
            names = [user.get_full_name() or user.username for user in assignees]
            return ", ".join(names)
        else:
            # Show first 2 names + count if more than 2
            first_two = list(assignees[:2])
            names = [user.get_full_name() or user.username for user in first_two]
            remaining_count = assignees.count() - 2
            return f"{', '.join(names)} +{remaining_count} more"
    
    get_assignees_display.short_description = 'Assigned To'
    get_assignees_display.admin_order_field = 'assigned_to'
    
    def is_overdue_display(self, obj):
        if obj.is_overdue():
            return format_html('<span style="color: red; font-weight: bold;">⚠️ Yes</span>')
        return format_html('<span style="color: green;">✓ No</span>')
    is_overdue_display.short_description = 'Overdue'
    
    # ADDED: Custom actions for bulk operations
    actions = ['mark_as_completed', 'mark_as_in_progress', 'mark_as_pending']
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated} task(s) marked as completed.')
    mark_as_completed.short_description = "Mark selected tasks as completed"
    
    def mark_as_in_progress(self, request, queryset):
        updated = queryset.update(status='in_progress')
        self.message_user(request, f'{updated} task(s) marked as in progress.')
    mark_as_in_progress.short_description = "Mark selected tasks as in progress"
    
    def mark_as_pending(self, request, queryset):
        updated = queryset.update(status='pending')
        self.message_user(request, f'{updated} task(s) marked as pending.')
    mark_as_pending.short_description = "Mark selected tasks as pending"


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['task', 'user', 'content_preview', 'is_internal', 'created_at']
    list_filter = ['is_internal', 'created_at', 'task__division']
    search_fields = ['content', 'task__title', 'user__username']
    ordering = ['-created_at']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'


@admin.register(TaskAttachment)
class TaskAttachmentAdmin(admin.ModelAdmin):
    list_display = ['filename', 'task', 'uploaded_by', 'file_size_display', 'uploaded_at']
    list_filter = ['uploaded_at', 'task__division']
    search_fields = ['filename', 'task__title', 'uploaded_by__username']
    ordering = ['-uploaded_at']
    
    def file_size_display(self, obj):
        size = obj.file_size
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"
    file_size_display.short_description = 'File Size'


@admin.register(TaskHistory)
class TaskHistoryAdmin(admin.ModelAdmin):
    list_display = ['task', 'user', 'action', 'timestamp']
    list_filter = ['action', 'timestamp', 'task__division']
    search_fields = ['task__title', 'user__username', 'action']
    ordering = ['-timestamp']
    readonly_fields = ['timestamp']


# ADDED: Project and ProjectFile admin if they exist
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['title', 'assigned_to_admin', 'division', 'created_by', 'created_at']
    list_filter = ['division', 'created_at', 'assigned_to_admin']
    search_fields = ['title', 'description', 'created_by__username']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Project Information', {
            'fields': ('title', 'description')
        }),
        ('Assignment', {
            'fields': ('assigned_to_admin', 'division', 'created_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProjectFile)
class ProjectFileAdmin(admin.ModelAdmin):
    list_display = ['filename', 'project', 'uploaded_by', 'file_size_display', 'uploaded_at']
    list_filter = ['uploaded_at', 'project']
    search_fields = ['filename', 'project__title', 'uploaded_by__username']
    ordering = ['-uploaded_at']
    readonly_fields = ['uploaded_at', 'file_size']
    
    def file_size_display(self, obj):
        """Display file size in human readable format"""
        if obj.file_size:
            size = obj.file_size
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} TB"
        return "Unknown"
    file_size_display.short_description = 'File Size'


# Custom admin site configuration
admin.site.site_header = "Task Manager Administration"
admin.site.site_title = "Task Manager Admin"
admin.site.index_title = "Welcome to Task Manager Administration"