import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// ✅ Shopify App Bridge — complete the session token handshake BEFORE rendering.
// Without this, App Bridge times out with "Transition was aborted" error.
async function initApp() {
  if (window.shopify) {
    try {
      // This tells App Bridge that the app has loaded and is ready.
      // It resolves the pending id_token exchange that Shopify is waiting for.
      await window.shopify.idToken();
    } catch (e) {
      // Not fatal — app will still render. Happens when running outside Shopify.
      console.warn('[AppBridge] idToken() failed (expected outside Shopify):', e?.message);
    }
  }

  createRoot(document.getElementById('root')).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}

initApp();
