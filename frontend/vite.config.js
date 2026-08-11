import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const repositoryName = process.env.GITHUB_REPOSITORY?.split('/')[1] || 'erionas-hiking-journal'

export default defineConfig({
  base: process.env.GITHUB_ACTIONS ? `/${repositoryName}/` : '/',
  plugins: [react()],
})