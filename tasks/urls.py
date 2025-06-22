from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

from .views import (
    CustomPasswordResetView,
    CustomPasswordResetDoneView,
    CustomPasswordResetConfirmView,
    CustomPasswordResetCompleteView,
)

urlpatterns = [
    # Authentication
    
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Tasks
    path('tasks/', views.task_list, name='task_list'),
    path('tasks/create/', views.task_create, name='task_create'),
    path('tasks/<int:task_id>/', views.task_detail, name='task_detail'),
    path('tasks/<int:task_id>/edit/', views.task_edit, name='task_edit'),
    path('tasks/<int:task_id>/update-status/', views.task_update_status, name='task_update_status'),
    path('tasks/<int:task_id>/delete/', views.delete_task, name='delete_task'),
    
    #Division Management
    path('divisions/', views.division_list, name='division_list'),
    path('divisions/create/', views.create_division, name='create_division'),
    path('divisions/<int:pk>/edit/', views.edit_division, name='edit_division'),
    path('divisions/<int:pk>/delete/', views.delete_division, name='delete_division'),

    
    # User Management
    path('users/', views.user_management, name='user_management'),
    path('users/<int:user_id>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),

    
    # Reports
    path('reports/', views.reports_dashboard, name='reports'),
    path('export/excel/', views.export_tasks_excel, name='export_excel'),
    path('reports/export/pdf/', views.export_tasks_pdf, name='export_tasks_pdf'),

    # password management
    path('password-reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

