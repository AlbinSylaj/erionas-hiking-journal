const databaseName = 'erionas-hiking-journal'
const storeName = 'trails'

function openDatabase() {
  return new Promise((resolve, reject) => {
    const request = window.indexedDB.open(databaseName, 1)
    request.onupgradeneeded = () => {
      const database = request.result
      if (!database.objectStoreNames.contains(storeName)) {
        database.createObjectStore(storeName, { keyPath: 'id' })
      }
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

async function runTransaction(mode, requestForStore) {
  const database = await openDatabase()
  return new Promise((resolve, reject) => {
    const transaction = database.transaction(storeName, mode)
    const request = requestForStore(transaction.objectStore(storeName))
    let result

    request.onsuccess = () => {
      result = request.result
    }
    request.onerror = () => reject(request.error)
    transaction.oncomplete = () => resolve(result)
    transaction.onerror = () => reject(transaction.error)
    transaction.onabort = () => reject(transaction.error)
  }).finally(() => database.close())
}

export async function listTrails() {
  const trails = await runTransaction('readonly', (store) => store.getAll())
  return trails.sort((firstTrail, secondTrail) => secondTrail.created_at.localeCompare(firstTrail.created_at))
}

export function saveTrail(trail) {
  return runTransaction('readwrite', (store) => store.put(trail))
}

export function deleteTrail(trailId) {
  return runTransaction('readwrite', (store) => store.delete(trailId))
}