import json
import hashlib
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from PIL import Image, UnidentifiedImageError

from .models import Trail


def fetch_json(url, data=None, timeout=10):
	request = Request(
		url,
		data=data.encode() if data else None,
		headers={
			'User-Agent': 'TrailLog/0.1 (local development)',
			'Content-Type': 'application/x-www-form-urlencoded',
		},
	)
	with urlopen(request, timeout=timeout) as response:
		return json.load(response)


def fetch_hiking_routes(query):
	parameters = urlencode({'data': query})
	last_error = None
	for endpoint in (
		'https://maps.mail.ru/osm/tools/overpass/api/interpreter',
		'https://overpass-api.de/api/interpreter',
		'https://overpass.kumi.systems/api/interpreter',
		'https://overpass.private.coffee/api/interpreter',
	):
		try:
			return fetch_json(endpoint, parameters, timeout=10)
		except (OSError, ValueError, json.JSONDecodeError) as error:
			last_error = error
	raise last_error


def find_trail_photo(trail_name, location):
	if not settings.SERPAPI_API_KEY:
		return None

	query = f'"{trail_name}" hiking {location}'
	cache_key = f"trail-photo:{hashlib.sha256(query.encode()).hexdigest()}"
	cached_photo = cache.get(cache_key)
	if cached_photo is not None:
		return cached_photo

	response = fetch_json('https://serpapi.com/search.json?' + urlencode({
		'api_key': settings.SERPAPI_API_KEY,
		'engine': 'google_images',
		'q': query,
		'location': location,
		'gl': 'de',
		'hl': 'en',
		'image_type': 'photo',
		'safe': 'active',
	}))
	images = response.get('images_results', [])
	if not images:
		return None

	image = images[0]
	photo = {
		'url': image.get('original', image['thumbnail']),
		'thumbnail_url': image['thumbnail'],
		'source_url': image['link'],
	}
	cache.set(cache_key, photo, 60 * 60 * 24)
	return photo


def find_hiking_routes(location, radius_km):
	geocode_url = 'https://nominatim.openstreetmap.org/search?' + urlencode({
		'format': 'jsonv2',
		'limit': 1,
		'q': location,
	})
	places = fetch_json(geocode_url)
	if not places:
		return None, []

	latitude = float(places[0]['lat'])
	longitude = float(places[0]['lon'])
	radius_m = min(max(radius_km, 1), 50) * 1000
	overpass_query = f'''[out:json][timeout:15];
(
	relation["route"="hiking"]["name"](around:{radius_m},{latitude},{longitude});
);
	out tags center 8;'''
	routes = fetch_hiking_routes(overpass_query)
	results = []
	for route in routes.get('elements', []):
		tags = route.get('tags', {})
		name = tags.get('name') or tags.get('ref')
		if name:
			route_latitude = route.get('center', {}).get('lat', latitude)
			route_longitude = route.get('center', {}).get('lon', longitude)
			try:
				photo = find_trail_photo(name, location)
			except (OSError, ValueError, json.JSONDecodeError):
				photo = None
			results.append({
				'id': f"osm-{route['type']}-{route['id']}",
				'name': name,
				'location': location,
				'latitude': route_latitude,
				'longitude': route_longitude,
				'difficulty': tags.get('sac_scale', 'unspecified').replace('_', ' '),
				'description': tags.get('description') or tags.get('note') or 'Mapped public hiking route.',
				'osm_url': f"https://www.openstreetmap.org/{route['type']}/{route['id']}",
				'photo': photo,
			})
	return places[0]['display_name'], results


def find_location_suggestions(query):
	url = 'https://nominatim.openstreetmap.org/search?' + urlencode({
		'format': 'jsonv2',
		'limit': 5,
		'featuretype': 'city',
		'q': query,
	})
	return [{'name': place['display_name']} for place in fetch_json(url)]


def serialize_trail(trail):
	return {
		'id': trail.id,
		'name': trail.name,
		'location': trail.location,
		'distance_km': float(trail.distance_km),
		'elevation_gain_m': trail.elevation_gain_m,
		'difficulty': trail.difficulty,
		'description': trail.description,
		'photo_url': trail.photo.url if trail.photo else None,
		'is_completed': trail.is_completed,
	}


def parse_payload(request):
	try:
		return json.loads(request.body)
	except json.JSONDecodeError:
		return None


def validate_payload(payload):
	required_fields = {'name', 'location', 'distance_km', 'elevation_gain_m', 'difficulty'}
	if not payload or not required_fields.issubset(payload):
		return 'Name, location, distance, elevation, and difficulty are required.'
	if payload['difficulty'] not in Trail.Difficulty.values:
		return 'Difficulty must be easy, moderate, or hard.'
	try:
		if Decimal(str(payload['distance_km'])) <= 0 or int(payload['elevation_gain_m']) < 0:
			return 'Distance must be positive and elevation cannot be negative.'
	except (InvalidOperation, TypeError, ValueError):
		return 'Distance and elevation must be valid numbers.'
	return None


def validate_photo(photo):
	if not photo:
		return None
	if photo.size > 5 * 1024 * 1024:
		return 'Photo must be 5 MB or smaller.'
	try:
		image = Image.open(photo)
		image.verify()
		photo.seek(0)
	except (UnidentifiedImageError, OSError):
		return 'Upload a valid image file.'
	return None


def trail_data(payload, photo=None):
	data = {
		'name': payload['name'].strip(),
		'location': payload['location'].strip(),
		'distance_km': payload['distance_km'],
		'elevation_gain_m': payload['elevation_gain_m'],
		'difficulty': payload['difficulty'],
		'description': payload.get('description', '').strip(),
		'is_completed': bool(payload.get('is_completed', False)),
	}
	if photo:
		data['photo'] = photo
	return data


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def trail_list(request):
	if request.method == 'GET':
		query = request.GET.get('search', '').strip()
		trails = Trail.objects.all()
		if query:
			trails = trails.filter(
				Q(name__icontains=query) | Q(location__icontains=query) | Q(description__icontains=query)
			)
		return JsonResponse({'trails': [serialize_trail(trail) for trail in trails]})

	is_multipart = request.content_type and request.content_type.startswith('multipart/form-data')
	payload = request.POST if is_multipart else parse_payload(request)
	error = validate_payload(payload)
	if error:
		return JsonResponse({'error': error}, status=400)
	photo = request.FILES.get('photo')
	error = validate_photo(photo)
	if error:
		return JsonResponse({'error': error}, status=400)
	trail = Trail.objects.create(**trail_data(payload, photo))
	return JsonResponse(serialize_trail(trail), status=201)


@require_http_methods(['GET'])
def discover_trails(request):
	location = request.GET.get('location', '').strip()
	if not location:
		return JsonResponse({'error': 'Enter a city, park, or region to discover trails.'}, status=400)
	try:
		radius_km = int(request.GET.get('radius_km', 25))
	except ValueError:
		return JsonResponse({'error': 'Radius must be a number.'}, status=400)
	try:
		place_name, trails = find_hiking_routes(location, radius_km)
	except (OSError, ValueError, json.JSONDecodeError):
		search_text = f'hiking trails near {location}'
		return JsonResponse({
			'location': location,
			'fallback': True,
			'trails': [{
				'id': f"search-{location.lower().replace(' ', '-')}",
				'name': search_text.title(),
				'location': location,
				'difficulty': 'check map',
				'description': 'The live public trail service is busy. Browse current hiking routes in Google Maps instead.',
				'osm_url': 'https://www.openstreetmap.org/search?' + urlencode({'query': search_text}),
			}],
		})
	if place_name is None:
		return JsonResponse({'error': 'Location not found. Try a city, park, or region name.'}, status=404)
	return JsonResponse({'location': place_name, 'trails': trails})


@require_http_methods(['GET'])
def location_suggestions(request):
	query = request.GET.get('query', '').strip()
	if len(query) < 2:
		return JsonResponse({'locations': []})
	try:
		locations = find_location_suggestions(query)
	except (OSError, ValueError, json.JSONDecodeError):
		return JsonResponse({'error': 'Location suggestions are temporarily unavailable.'}, status=503)
	return JsonResponse({'locations': locations})


@csrf_exempt
@require_http_methods(['PATCH', 'DELETE'])
def trail_detail(request, trail_id):
	try:
		trail = Trail.objects.get(pk=trail_id)
	except Trail.DoesNotExist:
		return JsonResponse({'error': 'Trail not found.'}, status=404)

	if request.method == 'DELETE':
		trail.delete()
		return JsonResponse({}, status=204)

	payload = parse_payload(request)
	error = validate_payload(payload)
	if error:
		return JsonResponse({'error': error}, status=400)
	for field, value in trail_data(payload).items():
		setattr(trail, field, value)
	trail.save()
	return JsonResponse(serialize_trail(trail))
