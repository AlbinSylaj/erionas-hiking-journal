from django.db import models


class Trail(models.Model):
	class Difficulty(models.TextChoices):
		EASY = 'easy', 'Easy'
		MODERATE = 'moderate', 'Moderate'
		HARD = 'hard', 'Hard'

	name = models.CharField(max_length=120)
	location = models.CharField(max_length=160)
	distance_km = models.DecimalField(max_digits=5, decimal_places=1)
	elevation_gain_m = models.PositiveIntegerField()
	difficulty = models.CharField(max_length=10, choices=Difficulty.choices)
	description = models.TextField(blank=True)
	photo = models.ImageField(upload_to='trail_photos/', blank=True)
	is_completed = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['is_completed', '-created_at']

	def __str__(self):
		return self.name
