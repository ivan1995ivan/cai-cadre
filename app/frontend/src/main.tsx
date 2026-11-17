import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import './i18n'
import './styles.css'
import App from './App'

if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js').catch(() => undefined))
}

// Validarea formelor (form.validateFields) respinge promisiunea cu {errorFields} când lipsește un câmp obligatoriu;
// câmpurile își arată deja eroarea, deci nu e o eroare a programului de scris în consolă
window.addEventListener('unhandledrejection', (e) => {
  if (e.reason && Array.isArray((e.reason as { errorFields?: unknown }).errorFields)) e.preventDefault()
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
