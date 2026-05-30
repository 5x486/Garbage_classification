from django.urls import path
from . import views

app_name = 'recognition'

urlpatterns = [
    path('image/', views.image_upload_view, name='image'),
    path('video/', views.video_upload_view, name='video'),
    path('camera/', views.camera_view, name='camera'),
    path('api/predict-image/', views.api_predict_image, name='api_predict_image'),
    path('api/predict-video/', views.api_predict_video, name='api_predict_video'),
    path('api/predict-frame/', views.api_predict_frame, name='api_predict_frame'),
    path('api/recent-records/', views.recent_records, name='api_recent_records'),
]
