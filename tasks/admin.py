from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, Division, Task, Comment, TaskAttachment, TaskHistory


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
    list_display = [
        'title', 'status', 'priority', 'assigned_to', 'division', 
        'created_by', 'due_date', 'is_overdue_display', 'created_at'
    ]
    list_filter = [
        'status', 'priority', 'division', 'created_at', 'due_date'
    ]
    search_fields = ['title', 'description', 'assigned_to__username', 'created_by__username']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'status', 'priority')
        }),
        ('Assignment', {
            'fields': ('created_by', 'assigned_to', 'division')
        }),
        ('Dates', {
            'fields': ('due_date', 'completed_at')
        }),
        ('Time Tracking', {
            'fields': ('estimated_hours', 'actual_hours')
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    inlines = [CommentInline, TaskAttachmentInline, TaskHistoryInline]
    
    def is_overdue_display(self, obj):
        if obj.is_overdue():
            return format_html('<span style="color: red;">Yes</span>')
        return 'No'
    is_overdue_display.short_description = 'Overdue'


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

