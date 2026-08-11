from django.urls import path

from . import views

urlpatterns = [
    path('trails/', views.trail_list, name='trail-list'),
    path('trails/<int:trail_id>/', views.trail_detail, name='trail-detail'),
    path('discover/', views.discover_trails, name='trail-discovery'),
    path('locations/', views.location_suggestions, name='location-suggestions'),
]