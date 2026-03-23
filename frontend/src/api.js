import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || ''

const client = axios.create({ baseURL: BASE })

export async function parseCV(cvFile) {
  const form = new FormData()
  form.append('cv', cvFile)
  const { data } = await client.post('/api/parse-cv', form)
  return data // { profile, profile_text }
}

export async function searchJobs({ field, location, positionType }) {
  const { data } = await client.post('/api/search-jobs', {
    field,
    location,
    position_type: positionType,
  })
  return data // { jobs }
}

export async function scoreJobs({ jobs, profileText }) {
  const { data } = await client.post('/api/score-jobs', {
    jobs,
    profile_text: profileText,
  })
  return data // { scored_jobs }
}

export async function prepareApplication({ job, profileText }) {
  const { data } = await client.post('/api/prepare', {
    job,
    profile_text: profileText,
  })
  return data // { hints, cover_letter }
}

export async function regenerateLetter({ job, profileText }) {
  const { data } = await client.post('/api/regenerate', {
    job,
    profile_text: profileText,
  })
  return data // { cover_letter }
}

export async function exportZip(approved) {
  const { data } = await client.post(
    '/api/export',
    { approved },
    { responseType: 'blob' }
  )
  return data // Blob
}
