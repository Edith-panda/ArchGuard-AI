import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './RemediationActions.css'
import './RemediationDock.css'
import App from './App.jsx'
import RemediationDock, { installAssistantResponseBridge } from './RemediationDock.jsx'

installAssistantResponseBridge()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <>
      <App />
      <RemediationDock />
    </>
  </StrictMode>,
)
