import { useEffect, useRef, useState } from 'react'
import { deleteTrail, listTrails, saveTrail as saveStoredTrail } from './journalStorage'

const emptyTrail = {
  name: '',
  location: '',
  distance_km: '',
  elevation_gain_m: '',
  difficulty: 'moderate',
  description: '',
}

const difficultyLabel = {
  easy: 'Easy',
  moderate: 'Moderate',
  hard: 'Hard',
}

function TrailPhoto({ photo, name }) {
  const [photoUrl, setPhotoUrl] = useState('')

  useEffect(() => {
    if (!photo) {
      setPhotoUrl('')
      return undefined
    }

    const objectUrl = URL.createObjectURL(photo)
    setPhotoUrl(objectUrl)
    return () => URL.revokeObjectURL(objectUrl)
  }, [photo])

  return photoUrl ? <img className="personal-trail-photo" src={photoUrl} alt={`Photo from ${name}`} /> : null
}

function App() {
  const [trails, setTrails] = useState([])
  const [form, setForm] = useState(emptyTrail)
  const [photoFile, setPhotoFile] = useState(null)
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [discoveryLocation, setDiscoveryLocation] = useState('Nuremberg, Germany')
  const [discoveredTrails, setDiscoveredTrails] = useState([])
  const [discoveryStatus, setDiscoveryStatus] = useState('')
  const [isDiscovering, setIsDiscovering] = useState(false)
  const [locationSuggestions, setLocationSuggestions] = useState([])
  const [isLocationFocused, setIsLocationFocused] = useState(false)
  const [status, setStatus] = useState('Loading your journal...')
  const [isSaving, setIsSaving] = useState(false)
  const photoInput = useRef(null)

  useEffect(() => {
    let isCurrent = true

    listTrails()
      .then((savedTrails) => {
        if (!isCurrent) return
        setTrails(savedTrails)
        setStatus('')
      })
      .catch(() => {
        if (isCurrent) setStatus('This browser could not open the private journal storage.')
      })

    return () => {
      isCurrent = false
    }
  }, [])

  useEffect(() => {
    const query = discoveryLocation.trim()
    if (query.length < 2) {
      setLocationSuggestions([])
      return undefined
    }

    const suggestionTimer = setTimeout(async () => {
      try {
        const response = await fetch(`https://nominatim.openstreetmap.org/search?format=jsonv2&limit=5&q=${encodeURIComponent(query)}`)
        if (!response.ok) return
        const places = await response.json()
        setLocationSuggestions(places.map((place) => ({ name: place.display_name })))
      } catch {
        setLocationSuggestions([])
      }
    }, 350)

    return () => clearTimeout(suggestionTimer)
  }, [discoveryLocation])

  async function saveTrail(event) {
    event.preventDefault()
    setIsSaving(true)
    setStatus('')
    try {
      const trail = {
        ...form,
        id: crypto.randomUUID(),
        distance_km: Number(form.distance_km),
        elevation_gain_m: Number(form.elevation_gain_m),
        is_completed: false,
        created_at: new Date().toISOString(),
        photo: photoFile || null,
      }
      await saveStoredTrail(trail)
      setTrails((currentTrails) => [trail, ...currentTrails])
      setForm(emptyTrail)
      setPhotoFile(null)
      if (photoInput.current) photoInput.current.value = ''
      setStatus('Trail added to your log.')
    } catch (error) {
      setStatus('Could not save this trail on the device.')
    } finally {
      setIsSaving(false)
    }
  }

  async function updateTrail(trail, changes) {
    const updatedTrail = { ...trail, ...changes }
    try {
      await saveStoredTrail(updatedTrail)
      setTrails((currentTrails) => currentTrails.map((item) => (item.id === trail.id ? updatedTrail : item)))
    } catch {
      setStatus('Could not update this trail on the device.')
    }
  }

  async function removeTrail(trail) {
    try {
      await deleteTrail(trail.id)
      setTrails((currentTrails) => currentTrails.filter((item) => item.id !== trail.id))
    } catch {
      setStatus('Could not remove this trail from the device.')
    }
  }

  async function discoverTrails(event) {
    event.preventDefault()
    setIsDiscovering(true)
    setDiscoveryStatus('')
    try {
      const placeResponse = await fetch(`https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&q=${encodeURIComponent(discoveryLocation)}`)
      const [place] = await placeResponse.json()
      if (!place) throw new Error('No matching place was found.')

      const routeQuery = `[out:json][timeout:25];relation["route"="hiking"](around:25000,${place.lat},${place.lon});out tags;`
      const routeResponse = await fetch('https://overpass-api.de/api/interpreter', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8' },
        body: `data=${encodeURIComponent(routeQuery)}`,
      })
      if (!routeResponse.ok) throw new Error('Public route data is busy.')

      const data = await routeResponse.json()
      const routes = data.elements
        .filter((route) => route.tags?.name)
        .slice(0, 12)
        .map((route) => ({
          id: route.id,
          name: route.tags.name,
          location: place.display_name,
          difficulty: route.tags.sac_scale?.includes('demanding') ? 'hard' : route.tags.sac_scale ? 'moderate' : 'easy',
          description: route.tags.description || route.tags.note || 'Public hiking route from OpenStreetMap.',
          osm_url: `https://www.openstreetmap.org/relation/${route.id}`,
        }))
      setDiscoveredTrails(routes)
      setDiscoveryStatus(routes.length ? `${routes.length} public routes near ${place.display_name}` : `No named hiking routes were found near ${place.display_name}.`)
    } catch (error) {
      setDiscoveredTrails([])
      setDiscoveryStatus(`${error.message} Try the Google Maps search below.`)
    } finally {
      setIsDiscovering(false)
    }
  }

  const completed = trails.filter((trail) => trail.is_completed).length
  const totalDistance = trails.reduce((sum, trail) => sum + Number(trail.distance_km), 0)
  const visibleTrails = trails.filter((trail) => {
    const matchesFilter = filter === 'all' || (filter === 'completed' ? trail.is_completed : !trail.is_completed)
    const searchableText = `${trail.name} ${trail.location} ${trail.description}`.toLowerCase()
    return matchesFilter && searchableText.includes(search.trim().toLowerCase())
  })

  return (
    <main>
      <section className="masthead">
        <div className="masthead-content">
          <p className="eyebrow">Eriona's personal hiking journal</p>
          <h1>Trail Log</h1>
          <p className="intro">Remember to keep away from avalanches, don't just stare and record them</p>
        </div>
        <div className="summit-mark" aria-hidden="true">TL</div>
      </section>

      <section className="metrics" aria-label="Trail summary">
        <div><strong>{trails.length}</strong><span>trails logged</span></div>
        <div><strong>{completed}</strong><span>completed</span></div>
        <div><strong>{totalDistance.toFixed(1)}</strong><span>kilometers</span></div>
      </section>

      <section className="discover-panel">
        <div><p className="eyebrow">Nature beyond the city</p><h2>Discover public hiking routes</h2></div>
        <form className="discover-form" onSubmit={discoverTrails}>
          <label>Suggested area<select value={['Munich, Germany', 'Nuremberg, Germany'].includes(discoveryLocation) ? discoveryLocation : ''} onChange={(event) => event.target.value && setDiscoveryLocation(event.target.value)}><option value="">Choose an area</option><option value="Nuremberg, Germany">Nuremberg and surrounds</option><option value="Munich, Germany">Munich and surrounds</option></select></label>
          <label className="location-input">Near<input value={discoveryLocation} onChange={(event) => setDiscoveryLocation(event.target.value)} onFocus={() => setIsLocationFocused(true)} onBlur={() => setIsLocationFocused(false)} placeholder="City, park, or region" />
            {isLocationFocused && locationSuggestions.length > 0 && <ul className="location-suggestions">
              {locationSuggestions.map((location) => <li key={location.name}><button type="button" onMouseDown={(event) => event.preventDefault()} onClick={() => { setDiscoveryLocation(location.name); setIsLocationFocused(false) }}>{location.name}</button></li>)}
            </ul>}
          </label>
          <button className="primary-button" disabled={isDiscovering}>{isDiscovering ? 'Searching...' : 'Find trails'}</button>
        </form>
        {discoveryStatus && <p className="discovery-status" role="status">{discoveryStatus}</p>}
        <a className="map-search-link" href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${discoveryLocation} hiking trails`)}`} target="_blank" rel="noreferrer">Search nearby hikes in Google Maps</a>
        {discoveredTrails.length > 0 && <div className="discovery-results">
          {discoveredTrails.map((trail) => <article className="discovery-card" key={trail.id}>
            <span className="difficulty">Difficulty: {trail.difficulty}</span><h3>{trail.name}</h3><p>{trail.description}</p>
            <div className="route-links">
              <a href={`https://www.google.com/search?tbm=isch&q=${encodeURIComponent(`${trail.name} ${trail.location} hike`)}`} target="_blank" rel="noreferrer">Find hike photos on Google</a>
              <a href={`https://translate.google.com/?sl=auto&tl=en&text=${encodeURIComponent(trail.description)}&op=translate`} target="_blank" rel="noreferrer">Translate to English</a>
              <a href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${trail.name}, ${trail.location}`)}`} target="_blank" rel="noreferrer">Open in Google Maps</a>
              <a href={trail.osm_url} target="_blank" rel="noreferrer">OpenStreetMap route</a>
            </div>
          </article>)}
        </div>}
      </section>

      <section className="workspace">
        <form className="trail-form" onSubmit={saveTrail}>
          <div className="section-heading">
            <p className="eyebrow">New route</p>
            <h2>Add a trail</h2>
          </div>
          <label>Trail name<input required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="e.g. Eagle Ridge Loop" /></label>
          <label>Location<input required value={form.location} onChange={(event) => setForm({ ...form, location: event.target.value })} placeholder="Park, region, or trailhead" /></label>
          <div className="form-grid">
            <label>Distance (km)<input required min="0.1" step="0.1" type="number" value={form.distance_km} onChange={(event) => setForm({ ...form, distance_km: event.target.value })} /></label>
            <label>Elevation (m)<input required min="0" type="number" value={form.elevation_gain_m} onChange={(event) => setForm({ ...form, elevation_gain_m: event.target.value })} /></label>
          </div>
          <label>Difficulty<select value={form.difficulty} onChange={(event) => setForm({ ...form, difficulty: event.target.value })}><option value="easy">Easy</option><option value="moderate">Moderate</option><option value="hard">Hard</option></select></label>
          <label>Notes<textarea value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} placeholder="Conditions, viewpoint, or a note for next time." rows="3" /></label>
          <label className="photo-input">Trail photo<input ref={photoInput} type="file" accept="image/*" onChange={(event) => setPhotoFile(event.target.files?.[0] || null)} /><span>{photoFile ? photoFile.name : 'Choose a photo from your iPhone Photos library or take a new one'}</span></label>
          <button className="primary-button" disabled={isSaving}>{isSaving ? 'Adding...' : 'Add trail'}</button>
        </form>

        <div className="trail-list-section">
          <div className="list-topline">
            <div className="section-heading"><p className="eyebrow">Your routes</p><h2>Trail collection</h2></div>
            <div className="filter-group" aria-label="Trail filter">
              {['all', 'planned', 'completed'].map((option) => <button key={option} className={filter === option ? 'filter active' : 'filter'} onClick={() => setFilter(option)}>{option}</button>)}
            </div>
          </div>
          <label className="search-field">
            <span>Search trails</span>
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Name, location, or notes" type="search" />
          </label>
          {status && <p className="status" role="status">{status}</p>}
          <div className="trail-list">
            {visibleTrails.map((trail) => (
              <article className={trail.is_completed ? 'trail-card completed' : 'trail-card'} key={trail.id}>
                <TrailPhoto photo={trail.photo} name={trail.name} />
                <div className="trail-main">
                  <div className="trail-title"><span className={`difficulty ${trail.difficulty}`}>{difficultyLabel[trail.difficulty]}</span><h3>{trail.name}</h3></div>
                  <p className="location">{trail.location}</p>
                  {trail.description && <p className="description">{trail.description}</p>}
                  <div className="trail-stats"><span>{trail.distance_km} km</span><span>{trail.elevation_gain_m} m ascent</span></div>
                </div>
                <div className="trail-actions">
                  <button className="complete-button" onClick={() => updateTrail(trail, { is_completed: !trail.is_completed })}>{trail.is_completed ? 'Completed' : 'Mark done'}</button>
                  <button className="delete-button" onClick={() => removeTrail(trail)} aria-label={`Remove ${trail.name}`}>Remove</button>
                </div>
              </article>
            ))}
            {!status && visibleTrails.length === 0 && <div className="empty-state"><p>No trails here yet.</p><span>Add one from a place you want to explore.</span></div>}
          </div>
        </div>
      </section>
    </main>
  )
}

export default App