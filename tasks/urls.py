from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

# urls.py - Enhanced URL patterns for project management

from django.urls import path

urlpatterns = [
    # Authentication URLs
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Task Management
    path('tasks/', views.task_list, name='task_list'),
    path('tasks/<int:task_id>/', views.task_detail, name='task_detail'),
    path('tasks/create/', views.task_create, name='task_create'),
    path('tasks/<int:task_id>/edit/', views.task_edit, name='task_edit'),
    path('tasks/<int:task_id>/delete/', views.delete_task, name='delete_task'),
    path('tasks/<int:task_id>/update-status/', views.task_update_status, name='task_update_status'),
    
    # Project Management
    path('projects/', views.project_list, name='project_list'),
    path('projects/create/', views.project_create, name='project_create'),
    path('projects/<int:project_id>/', views.project_detail, name='project_detail'),
    path('projects/<int:project_id>/edit/', views.project_edit, name='project_edit'),
    path('projects/<int:project_id>/delete/', views.project_delete, name='project_delete'),
    
    # Task creation within projects
    path('projects/<int:project_id>/tasks/create/', views.task_create, name='project_task_create'),
    
    # My Projects (for users to see their assigned projects)
    path('my-projects/', views.my_projects, name='my_projects'),
    
    # Project Files Management
    path('project-files/<int:file_id>/delete/', views.project_file_delete, name='project_file_delete'),
    
    # User Management
    path('users/', views.user_management, name='user_management'),
    path('users/<int:user_id>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    path('users/<int:user_id>/delete/', views.delete_user, name='delete_user'),

    
    # Division Management
    path('divisions/', views.division_list, name='division_list'),
    path('divisions/create/', views.create_division, name='create_division'),
    path('divisions/<int:pk>/edit/', views.edit_division, name='edit_division'),
    path('divisions/<int:pk>/delete/', views.delete_division, name='delete_division'),
    
    # Reports
    path('reports/', views.reports_dashboard, name='reports'),
    path('reports/export/excel/', views.export_tasks_excel, name='export_tasks_excel'),
    path('reports/export/pdf/', views.export_tasks_pdf, name='export_tasks_pdf'),
    
    # AJAX Endpoints
    path('ajax/get-division-admins/', views.get_division_admins, name='get_division_admins'),
    path('download-file/<int:file_id>/', views.download_project_file, name='download_project_file'),
    path('view-file/<int:file_id>/', views.view_project_file, name='view_project_file'),
    path('tasks/<int:task_id>/add-comment/', views.add_comment_ajax, name='add_comment_ajax'),
    
    # Password Reset URLs
    path('password-reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset-complete/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

