import { useState, useEffect } from 'react';
import axios from 'axios';
import Header from './components/Header';
import DashboardView from './components/DashboardView';
import Settings from './components/Settings';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard'); 
  
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  
  // ✅ Stores ab dynamic hain (hardcoded nahi)
  const [stores, setStores] = useState([]);
  const [selectedStore, setSelectedStore] = useState('');
  
  const [markup, setMarkup] = useState(() => localStorage.getItem('global_markup') || '0');
  const [markupType, setMarkupType] = useState(() => localStorage.getItem('global_markup_type') || 'percent');
  const [extraPercent, setExtraPercent] = useState(() => localStorage.getItem('global_extra_percent') || '0');
  const [taxRate, setTaxRate] = useState(() => localStorage.getItem('global_tax_rate') || '0');

  const [collections, setCollections] = useState([]);
  const [selectedCollections, setSelectedCollections] = useState([]);

  // ✅ DYNAMIC API URL: Yeh khud detect karega ke aap kis URL par ho
  // Agar aap Railway par ho toh Railway ka URL, cPanel par ho toh cPanel ka URL
  const API_URL = import.meta.env.VITE_API_URL || `${window.location.origin}/api/shopify`;

  // 1. Connected Stores Fetch Karein
  useEffect(() => {
    const fetchStores = async () => {
      try {
        const res = await axios.get(`${API_URL}/stores`);
        setStores(res.data);
        if (res.data.length > 0) {
          setSelectedStore(res.data[0].shop_domain);
        }
      } catch (err) {
        console.error("Failed to fetch stores", err);
      }
    };
    fetchStores();
  }, [API_URL]);

  // 2. Jab Store Change ho toh uski Collections Fetch karein
  useEffect(() => {
    const fetchCollections = async () => {
      if (!selectedStore) return;
      try {
        const res = await axios.get(`${API_URL}/collections?shop=${selectedStore}`);
        if (res.data.collections) setCollections(res.data.collections);
      } catch (err) {
        console.error("Failed to fetch collections", err);
      }
    };
    fetchCollections();
  }, [selectedStore, API_URL]);

  // 3. Naya Store Connect Karne ka Function (FIXED)
  const handleConnectStore = () => {
    const newShop = prompt("Enter your Shopify store URL (e.g., your-store.myshopify.com)");
    if (newShop) {
      // ✅ Railway wala purana URL hata kar dynamic URL lagaya hai
      window.location.href = `${window.location.origin}/api/shopify/install?shop=${newShop}`;
    }
  };

  const handlePushToShopify = async () => {
    if (!url) return setError('Please enter an Amazon URL');
    if (!selectedStore) return setError('Please connect a Shopify store first');
    
    setLoading(true);
    setError('');
    setSuccessMsg('');

    try {
      const res = await axios.post(`${API_URL}/app/add-product`, { 
        amazon_url: url,
        shop_domain: selectedStore,
        markup: parseFloat(markup),
        markup_type: markupType,
        extra_percent: parseFloat(extraPercent),
        tax_rate: parseFloat(taxRate),
        collection_ids: selectedCollections
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
    setMarkupType(localStorage.getItem('global_markup_type') || 'percent');
    setExtraPercent(localStorage.getItem('global_extra_percent') || '0');
    setTaxRate(localStorage.getItem('global_tax_rate') || '0');
    setActiveTab('dashboard');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 dark:from-gray-900 dark:via-gray-900 dark:to-slate-900 transition-colors duration-300 flex flex-col items-center w-full overflow-x-hidden">
      
      <Header activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="w-full max-w-5xl p-4 md:p-6 mt-4 md:mt-6">
        
        {/* ✅ Hamesha Connect Store Button Dikhayein */}
        {activeTab === 'dashboard' && (
          <div className="bg-blue-50 border-l-4 border-blue-500 text-blue-700 p-4 mb-6 rounded shadow-sm flex justify-between items-center">
            <p>Connect a new Shopify store to manage its products.</p>
            <button onClick={handleConnectStore} className="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded transition">
              + Connect New Store
            </button>
          </div>
        )}

        {activeTab === 'dashboard' ? (
          <DashboardView 
            url={url} setUrl={setUrl}
            loading={loading} onSubmit={handlePushToShopify}
            stores={stores} selectedStore={selectedStore} setSelectedStore={setSelectedStore}
            collections={collections} selectedCollections={selectedCollections} setSelectedCollections={setSelectedCollections}
            markup={markup} markupType={markupType} extraPercent={extraPercent} taxRate={taxRate}
            error={error} successMsg={successMsg}
            onConnectStore={handleConnectStore}
          />
        ) : (
          <Settings onBack={handleBackFromSettings} />
        )}
      </main>

    </div>
  );
}