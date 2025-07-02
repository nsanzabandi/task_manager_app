# Create this file: your_app/templatetags/task_extras.py

from django import template

register = template.Library()

@register.filter
def is_assigned_to(task, user):
    """Check if a user is assigned to a task"""
    if hasattr(task, 'is_assigned_to_user'):
        return task.is_assigned_to_user(user)
    return False

@register.filter
def can_edit_task(task, user):
    """Check if user can edit the task"""
    if hasattr(task, 'can_user_edit'):
        return task.can_user_edit(user)
    return False