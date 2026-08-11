import json
import tempfile
from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from django.urls import reverse

from .models import Trail


class TrailApiTests(TestCase):
	payload = {
		'name': 'Eagle Ridge Loop',
		'location': 'North Cascades, WA',
		'distance_km': 8.4,
		'elevation_gain_m': 520,
		'difficulty': 'moderate',
		'description': 'A forested loop with a broad summit view.',
	}

	def test_can_create_and_list_trails(self):
		response = self.client.post(
			reverse('trail-list'), data=json.dumps(self.payload), content_type='application/json'
		)

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.json()['name'], self.payload['name'])

		response = self.client.get(reverse('trail-list'))
		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.json()['trails']), 1)

	def test_can_mark_trail_complete(self):
		trail = Trail.objects.create(**self.payload)
		updated_payload = {**self.payload, 'is_completed': True}

		response = self.client.patch(
			reverse('trail-detail', args=[trail.id]),
			data=json.dumps(updated_payload),
			content_type='application/json',
		)

		self.assertEqual(response.status_code, 200)
		trail.refresh_from_db()
		self.assertTrue(trail.is_completed)

	def test_can_search_trails_by_name_location_or_notes(self):
		matching_trail = Trail.objects.create(**self.payload)
		Trail.objects.create(
			name='Cedar Creek Trail',
			location='Olympic Peninsula, WA',
			distance_km=5.2,
			elevation_gain_m=210,
			difficulty='easy',
			description='A quiet riverside walk.',
		)

		response = self.client.get(reverse('trail-list'), {'search': 'summit'})

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()['trails'], [
			{
				'id': matching_trail.id,
				'name': self.payload['name'],
				'location': self.payload['location'],
				'distance_km': self.payload['distance_km'],
				'elevation_gain_m': self.payload['elevation_gain_m'],
				'difficulty': self.payload['difficulty'],
				'description': self.payload['description'],
				'photo_url': None,
				'is_completed': False,
			}
		])

	def test_can_add_a_trail_photo(self):
		image_buffer = BytesIO()
		Image.new('RGB', (1, 1), 'green').save(image_buffer, format='PNG')
		with tempfile.TemporaryDirectory() as media_root:
			with self.settings(MEDIA_ROOT=media_root):
				response = self.client.post(
					reverse('trail-list'),
					data={
						**self.payload,
						'photo': SimpleUploadedFile('summit.png', image_buffer.getvalue(), content_type='image/png'),
					},
				)

		self.assertEqual(response.status_code, 201)
		self.assertTrue(response.json()['photo_url'].startswith('/media/trail_photos/'))

	@patch('trails.views.find_trail_photo')
	@patch('trails.views.fetch_hiking_routes')
	@patch('trails.views.fetch_json')
	def test_can_discover_hiking_routes_near_a_location(self, fetch_json, fetch_hiking_routes, find_trail_photo):
		fetch_json.return_value = [
			{'lat': '48.1374', 'lon': '11.5755', 'display_name': 'Munich, Bavaria, Germany'},
		]
		fetch_hiking_routes.return_value = {'elements': [{'type': 'relation', 'id': 42, 'center': {'lat': 48.12, 'lon': 11.57}, 'tags': {'name': 'Isar hiking route', 'route': 'hiking'}}]}
		find_trail_photo.return_value = {
			'url': 'https://example.com/isar-hike.jpg',
			'thumbnail_url': 'https://example.com/isar-hike-thumbnail.jpg',
			'source_url': 'https://example.com/isar-hike',
		}

		response = self.client.get(reverse('trail-discovery'), {'location': 'Munich, Germany'})

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()['location'], 'Munich, Bavaria, Germany')
		self.assertEqual(response.json()['trails'][0]['name'], 'Isar hiking route')
		self.assertEqual(response.json()['trails'][0]['latitude'], 48.12)
		self.assertEqual(response.json()['trails'][0]['photo']['thumbnail_url'], 'https://example.com/isar-hike-thumbnail.jpg')

	@patch('trails.views.fetch_json')
	def test_can_suggest_city_locations(self, fetch_json):
		fetch_json.return_value = [
			{'display_name': 'Nuremberg, Bavaria, Germany'},
			{'display_name': 'Nuremberg, Pennsylvania, United States'},
		]

		response = self.client.get(reverse('location-suggestions'), {'query': 'Nuremberg'})

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()['locations'][0]['name'], 'Nuremberg, Bavaria, Germany')

	@patch('trails.views.find_hiking_routes', side_effect=OSError)
	def test_returns_google_search_fallback_when_route_service_is_busy(self, find_hiking_routes):
		response = self.client.get(reverse('trail-discovery'), {'location': 'Munich, Germany'})

		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.json()['fallback'])
		self.assertEqual(response.json()['trails'][0]['name'], 'Hiking Trails Near Munich, Germany')

# Create your tests here.
