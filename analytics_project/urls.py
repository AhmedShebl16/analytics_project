from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Add this block:
schema_view = get_schema_view(
    openapi.Info(
        title="Sales Analytics API",
        default_version="v1",
        description="Extract → Analyze → Report endpoints",
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("analytics.urls")),

    # Swagger/OpenAPI
    path("swagger.json", schema_view.without_ui(cache_timeout=0), name="schema-json"),
    path("swagger/",   schema_view.with_ui("swagger",   cache_timeout=0), name="schema-swagger-ui"),
    path("redoc/",     schema_view.with_ui("redoc",     cache_timeout=0),   name="schema-redoc"),
]
