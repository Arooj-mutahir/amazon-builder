import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

async function initApp() {
  if (window.shopify) {
    try {
      await window.shopify.idToken();
    } catch (e) {
      console.warn('[AppBridge] idToken() failed (expected outside Shopify):', e?.message);
    }
  }

  createRoot(document.getElementById('root')).render(
    <StrictMode>
      {/* ✅ AppProvider hata dein, sirf App render karein */}
      <App />
    </StrictMode>,
  );
}

initApp();