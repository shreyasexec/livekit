import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    https: {
      key: fs.readFileSync('/etc/ssl/private/localhost-key.pem'),
      cert: fs.readFileSync('/etc/ssl/certs/localhost.pem'),
    },
  },
})
