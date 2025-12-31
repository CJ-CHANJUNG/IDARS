import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './styles/DesignSystem.css'
import App from './App.jsx'
import PDFViewerStandalone from './components/PDFViewerStandalone.jsx'

// Check if this is a pop-out viewer window
const urlParams = new URLSearchParams(window.location.search);
const isViewerMode = urlParams.get('mode') === 'viewer';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {isViewerMode ? <PDFViewerStandalone /> : <App />}
  </StrictMode>,
)
