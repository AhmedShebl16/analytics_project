from rest_framework.views import APIView
from rest_framework.response import Response
from celery.result import AsyncResult
from .tasks import extract_data, analyze_data, generate_report
import math
import pandas as pd

class ExtractDataView(APIView):
    def post(self, request):
        task = extract_data.delay()
        return Response({"task_id": task.id})

class AnalyzeDataView(APIView):
    def post(self, request):
        task = analyze_data.delay()
        return Response({"task_id": task.id})

class GenerateReportView(APIView):
    def post(self, request):
        task = generate_report.delay()
        return Response({"task_id": task.id})

class TaskStatusView(APIView):
    def get(self, request, task_id):
        result = AsyncResult(task_id)
        data = {"status": result.status}
        if result.ready():
            data["result"] = result.result
        return Response(data)

class StatsForecastView(APIView):
    """
    Synchronous JSON endpoint for stats & forecast.
    """
    def get(self, request):
        data = analyze_data()

        # 1) Sanitize customer_stats_sample
        for rec in data.get("customer_stats_sample", []):
            for field, val in rec.items():
                # NaN → None
                if isinstance(val, float) and math.isnan(val):
                    rec[field] = None
                # Pandas Timestamp → ISO string
                elif isinstance(val, pd.Timestamp):
                    rec[field] = val.isoformat()
                # "NaT" string → None
                elif val == "NaT":
                    rec[field] = None

        # 2) Sanitize weekly_sales_tail: keys are Timestamps
        raw_weekly = data.get("weekly_sales_tail", {})
        clean_weekly = {}
        for k, v in raw_weekly.items():
            # convert Timestamp keys
            if isinstance(k, pd.Timestamp):
                key = k.isoformat()
            else:
                key = str(k)
            clean_weekly[key] = v
        data["weekly_sales_tail"] = clean_weekly

        # 3) Sanitize forecast_next_week
        forecast = data.get("forecast_next_week")
        if isinstance(forecast, float) and math.isnan(forecast):
            data["forecast_next_week"] = None

        return Response(data)