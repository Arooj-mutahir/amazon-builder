import { useState, useEffect } from 'react';
import axios from 'axios';
import Header from './components/Header';
import DashboardView from './components/DashboardView';
import Settings from './components/Settings';

// ─── Helper: read ?shop= from URL (injected by Shopify App Bridge) ───
const getShopFromUrl = () => {
  const params = new URLSearchParams(window.location.search);
  return params.get('shop') || params.get('shopify_shop') || null;
};

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');

  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // ✅ Auto-detect store from ?shop= URL param (set by Shopify App Bridge)
  const [selectedStore, setSelectedStore] = useState(() => getShopFromUrl() || '');
  const [storeConnected, setStoreConnected] = useState(false);

  const [markup, setMarkup] = useState(() => localStorage.getItem('global_markup') || '0');
  const [markupType, setMarkupType] = useState(() => localStorage.getItem('global_markup_type') || 'fixed');
  const [extraPercent, setExtraPercent] = useState(() => localStorage.getItem('global_extra_percent') || '0');
  const [taxRate, setTaxRate] = useState(() => localStorage.getItem('global_tax_rate') || '0');

  const [collections, setCollections] = useState([]);
  const [selectedCollections, setSelectedCollections] = useState([]);

  const API_URL = import.meta.env.VITE_API_URL || `${window.location.origin}/api/shopify`;

  // ✅ On load: verify the store is connected + load its DB markup settings
  useEffect(() => {
    const shop = getShopFromUrl();
    if (!shop) return;
    if (shop !== selectedStore) setSelectedStore(shop);

    const verifyStore = async () => {
      try {
        const res = await axios.get(`${API_URL}/stores/by-shop?shop=${encodeURIComponent(shop)}`);
        const data = res.data;
        setStoreConnected(true);

        // Load markup from DB so Settings and PricingSummary always reflect live DB values
        const m  = String(data.markup       ?? 0);
        const mt = data.markup_type         || 'fixed';
        const ep = String(data.extra_percent ?? 0);
        const tr = String(data.tax_rate      ?? 0);

        setMarkup(m);
        setMarkupType(mt);
        setExtraPercent(ep);
        setTaxRate(tr);
        localStorage.setItem('global_markup',        m);
        localStorage.setItem('global_markup_type',   mt);
        localStorage.setItem('global_extra_percent', ep);
        localStorage.setItem('global_tax_rate',      tr);
      } catch (err) {
        console.warn('Store not connected or lookup failed:', err.response?.data?.detail || err.message);
        setStoreConnected(false);
      }
    };
    verifyStore();
  }, [API_URL]);

  // ✅ Fetch collections whenever the auto-detected store is known
  useEffect(() => {
    if (!selectedStore) return;
    const fetchCollections = async () => {
      try {
        const res = await axios.get(`${API_URL}/collections?shop=${selectedStore}`);
        if (res.data.collections) setCollections(res.data.collections);
      } catch (err) {
        console.error('Failed to fetch collections', err);
      }
    };
    fetchCollections();
  }, [selectedStore, API_URL]);

  // ✅ Install flow: redirect to backend /install with shop param
  const handleConnectStore = () => {
    const shopFromUrl = getShopFromUrl();
    if (shopFromUrl) {
      window.location.href = `${window.location.origin}/api/shopify/install?shop=${shopFromUrl}`;
    } else {
      const newShop = prompt('Enter your Shopify store URL (e.g., your-store.myshopify.com)');
      if (newShop) {
        window.location.href = `${window.location.origin}/api/shopify/install?shop=${newShop}`;
      }
    }
  };

  const handlePushToShopify = async () => {
    if (!url) return setError('Please enter an Amazon URL');
    if (!selectedStore) return setError('Store not detected. Please open this app from inside Shopify Admin.');

    setLoading(true);
    setError('');
    setSuccessMsg('');

    try {
      const res = await axios.post(`${API_URL}/app/add-product`, {
        amazon_url:       url,
        shop_domain:      selectedStore,   // ← auto-detected from ?shop= URL param
        markup:           parseFloat(markup),
        markup_type:      markupType,
        extra_percent:    parseFloat(extraPercent),
        tax_rate:         parseFloat(taxRate),
        collection_ids:   selectedCollections,
      });

      setSuccessMsg(`✅ ${res.data.message} (ASIN: ${res.data.asin}). Check backend terminal.`);
      setUrl('');
      setSelectedCollections([]);
    } catch (err) {
      if (err.response?.status === 409) {
        setError(`⚠️ ${err.response.data.detail}`);
      } else {
        setError(err.response?.data?.detail || 'Failed to connect to backend.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleBackFromSettings = () => {
    setMarkup(localStorage.getItem('global_markup') || '0');
    setMarkupType(localStorage.getItem('global_markup_type') || 'fixed');
    setExtraPercent(localStorage.getItem('global_extra_percent') || '0');
    setTaxRate(localStorage.getItem('global_tax_rate') || '0');
    setActiveTab('dashboard');
  };

  const isEmbedded = Boolean(getShopFromUrl());

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 dark:from-gray-900 dark:via-gray-900 dark:to-slate-900 transition-colors duration-300 flex flex-col items-center w-full overflow-x-hidden">

      <Header activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="w-full max-w-5xl p-4 md:p-6 mt-4 md:mt-6">

        {/* ✅ Show connect banner only when NOT embedded and store is unknown */}
        {activeTab === 'dashboard' && !selectedStore && !isEmbedded && (
          <div className="bg-blue-50 border-l-4 border-blue-500 text-blue-700 p-4 mb-6 rounded shadow-sm flex justify-between items-center">
            <p>Connect a Shopify store to manage its products.</p>
            <button onClick={handleConnectStore} className="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded transition">
              + Connect Store
            </button>
          </div>
        )}

        {activeTab === 'dashboard' ? (
          <DashboardView
            url={url} setUrl={setUrl}
            loading={loading} onSubmit={handlePushToShopify}
            selectedStore={selectedStore}
            storeConnected={storeConnected}
            collections={collections}
            selectedCollections={selectedCollections}
            setSelectedCollections={setSelectedCollections}
            markup={markup} markupType={markupType}
            extraPercent={extraPercent} taxRate={taxRate}
            error={error} successMsg={successMsg}
            onConnectStore={handleConnectStore}
          />
        ) : (
          <Settings
            onBack={handleBackFromSettings}
            shopDomain={selectedStore}
          />
        )}
      </main>

    </div>
  );
}
