"""
URL configuration for task_manager project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.http import FileResponse, Http404
from tasks.views import home
import os

def serve_static_file(request, path):
    """Manual static file serving"""
    static_dir = str(settings.STATICFILES_DIRS[0])
    file_path = os.path.join(static_dir, path)
    
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(open(file_path, 'rb'))
    else:
        raise Http404(f"File not found: {file_path}")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('', include('tasks.urls')),
    path('tinymce/', include('tinymce.urls')),
    # Manual static file serving
    path('static/<path:path>', serve_static_file, name='static_files'),
]

# Serve media files
if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)