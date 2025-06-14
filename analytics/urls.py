from django.urls import path
from .views import (
    ExtractDataView, AnalyzeDataView, GenerateReportView,
    TaskStatusView, StatsForecastView
)

urlpatterns = [
    path("extract/", ExtractDataView.as_view(),   name="extract-data"),
    path("analyze/", AnalyzeDataView.as_view(),   name="analyze-data"),
    path("report/",  GenerateReportView.as_view(), name="generate-report"),
    path("status/<str:task_id>/", TaskStatusView.as_view(), name="task-status"),
    path("stats/",   StatsForecastView.as_view(), name="stats-forecast"),
]
