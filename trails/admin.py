from django.contrib import admin
from .models import Trail


@admin.register(Trail)
class TrailAdmin(admin.ModelAdmin):
	list_display = ('name', 'location', 'difficulty', 'distance_km', 'is_completed')
	list_filter = ('difficulty', 'is_completed')
	search_fields = ('name', 'location')
