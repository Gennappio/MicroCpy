import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true,                 // bind 0.0.0.0 so Docker / other hosts can reach the dev server
    open: !process.env.NO_OPEN, // auto-open the browser natively; suppressed in containers (NO_OPEN=1)
  }
})
