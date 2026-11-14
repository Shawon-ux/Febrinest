from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("dashboard/", include("store.dashboard_urls")),
    path("", include("store.urls")),
    # Serves uploaded images (fine for small shops; use S3/Cloudinary when scaling).
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
