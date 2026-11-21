// src/App.jsx
import { useState, useEffect, useCallback, Component } from 'react';
import axios from 'axios';
import { AlertTriangle, Sparkles, Loader2, Clock, ShieldAlert } from 'lucide-react'; 

import DashboardView from './components/DashboardView';
import Settings from './components/Settings';
import ManualSync from './components/ManualSync';
import ImportModal from './components/ImportModal';
import Billing from './components/Billing'; 
import { usePlan } from './hooks/usePlan'; 

const BACKEND_URL = "https://amazon-builder-production.up.railway.app";
const API_URL = `${BACKEND_URL}/api/shopify`;

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true };
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 flex flex-col items-center justify-center text-center h-full">
          <AlertTriangle size={48} className="text-red-500 mb-4" />
          <h2 className="text-xl font-bold text-gray-900 mb-2">Kuch Gadbad Ho Gayi!</h2>
          <p className="text-gray-500 mb-4">Page load karte waqt error aa gaya. Kripya page refresh karein.</p>
          <button onClick={() => window.location.reload()} className="bg-gray-900 text-white px-4 py-2 rounded-lg">
            Refresh Page
          </button>
        </div>
      );
    }
    return this.props.children; 
  }
}

export default function App() {
  // 🔥 NAYE fields destructure kiye
  const { 
    isAdvance, isBasic, isExpired, plan, status, 
    daysLeftInTrial, productCount, productLimit, 
    loading: planLoading 
  } = usePlan();

  const [activeTab, setActiveTab] = useState('dashboard');
  const [isAutoSyncEnabled, setIsAutoSyncEnabled] = useState(null);
  
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalKey, setModalKey] = useState(0); 

  const [stores, setStores] = useState([]);
  const [selectedStore, setSelectedStore] = useState('');
  const [selectedStoreId, setSelectedStoreId] = useState(null);

  const [markup, setMarkup] = useState(() => localStorage.getItem('global_markup') || '0');
  const [markupType, setMarkupType] = useState(() => localStorage.getItem('global_markup_type') || 'percent');
  const [extraPercent, setExtraPercent] = useState(() => localStorage.getItem('global_extra_percent') || '0');
  const [taxRate, setTaxRate] = useState(() => localStorage.getItem('global_tax_rate') || '0');
  const [comparePriceMarkup, setComparePriceMarkup] = useState(() => localStorage.getItem('global_compare_markup') || '0');

  const [collections, setCollections] = useState([]);
  const [selectedCollections, setSelectedCollections] = useState([]);

  // 🔥 TOKEN EXCHANGE LOGIC
  useEffect(() => {
    const exchangeTokenAndFetchStores = async () => {
      try {
        const urlParams = new URLSearchParams(window.location.search);
        const shopFromUrl = urlParams.get('shop');

        if (!shopFromUrl) {
          console.warn("Shopify shop parameter nahi mila.");
          return;
        }

        let sessionToken = null;
        if (window.shopify && window.shopify.idToken) {
          try {
            sessionToken = await window.shopify.idToken();
          } catch (e) {
            console.error("ID Token error:", e);
          }
        }

        if (sessionToken) {
          console.log("🔄 Sending token to backend for:", shopFromUrl);
          await axios.post(`${API_URL}/token-exchange`, {
            shop: shopFromUrl,
            id_token: sessionToken
          });
          console.log("✅ Store saved to database via token exchange.");
        } else {
          console.warn("⚠️ ID Token nahi mila. App Bridge check karein.");
        }

        const res = await axios.get(`${API_URL}/stores`);
        setStores(res.data);

        if (res.data.length > 0) {
          const foundStore = res.data.find(s => s.shop_domain === shopFromUrl) || res.data[0];
          setSelectedStore(foundStore.shop_domain);
          setSelectedStoreId(foundStore.id);
        }
      } catch (err) {
        console.error("❌ Token exchange / fetch stores fail:", err);
      }
    };
    
    exchangeTokenAndFetchStores();
  }, []);

  // ✅ URL-based initial tab detection
  useEffect(() => {
    if (planLoading) return;
    if (isAdvance === undefined || isAdvance === null) return;

    const path = window.location.pathname;
    if (path.includes('settings')) setActiveTab('settings');
    else if (path.includes('manual-sync')) {
      if (!isAdvance) {
        setActiveTab('billing');
        window.history.replaceState({}, '', '/billing'); 
      } else {
        setActiveTab('manual-sync');
      }
    }
    else if (path.includes('billing')) setActiveTab('billing');
    else setActiveTab('dashboard');
  }, [isAdvance, planLoading]);

  // Keep selectedStoreId in sync
  useEffect(() => {
    if (!selectedStore || stores.length === 0) return;
    const store = stores.find(s => s.shop_domain === selectedStore);
    if (store && store.id !== selectedStoreId) {
      setSelectedStoreId(store.id);
    }
  }, [selectedStore, stores, selectedStoreId]);

  // Fetch collections
  useEffect(() => {
    let cancelled = false;
    const fetchCollections = async () => {
      setSelectedCollections([]);
      setCollections([]);
      if (!selectedStore) return;

      try {
        const res = await axios.get(`${API_URL}/collections?shop=${selectedStore}`);
        if (!cancelled && res.data.collections) {
          setCollections(res.data.collections);
        }
      } catch (err) {
        console.error("Failed to fetch collections", err);
      }
    };
    fetchCollections();
    return () => { cancelled = true; };
  }, [selectedStore]);

  // ✅ Auto-sync status sirf Advance user ke liye fetch karo
  useEffect(() => {
    const fetchAutoSyncStatus = async () => {
      if (!selectedStoreId) return;
      if (!isAdvance) {
        setIsAutoSyncEnabled(false); 
        return;
      }
      try {
        const res = await axios.get(`${API_URL}/auto-sync/status?store_id=${selectedStoreId}`);
        setIsAutoSyncEnabled(res.data.enabled);
      } catch (err) {
        console.error("Failed to fetch auto-sync status", err);
        setIsAutoSyncEnabled(false);
      }
    };
    fetchAutoSyncStatus();
  }, [selectedStoreId, isAdvance]);

  // ✅ handleToggleAutoSync par plan guard
  const handleToggleAutoSync = useCallback(async () => {
    if (!isAdvance) {
      alert("Auto-Sync is an Advance Plan feature. Please upgrade.");
      return;
    }
    if (isAutoSyncEnabled === null) return;
    const newState = !isAutoSyncEnabled;
    setIsAutoSyncEnabled(newState);

    try {
      await axios.post(`${API_URL}/auto-sync/toggle?store_id=${selectedStoreId}`, {
        enabled: newState
      });
    } catch (err) {
      console.error("Failed to update auto-sync", err);
      setIsAutoSyncEnabled(!newState);
      alert("Failed to update Auto-Sync setting.");
    }
  }, [isAdvance, isAutoSyncEnabled, selectedStoreId]);

  const handleModalImport = useCallback(async (importUrl) => {
    if (!importUrl) { setError("Please enter a valid URL"); return; }
    if (!selectedStore) { setError("Please connect a Shopify store first"); return; }

    setLoading(true);
    setError('');
    setSuccessMsg('');

    try {
      const payloadExtra = isAdvance ? parseFloat(extraPercent || 0) : 0;
      const payloadTax = isAdvance ? parseFloat(taxRate || 0) : 0;
      const payloadCompare = isAdvance ? parseFloat(comparePriceMarkup || 0) : 0;

      const res = await axios.post(`${API_URL}/app/add-product`, {
        amazon_url: importUrl,
        shop_domain: selectedStore,
        markup: parseFloat(markup || 0),
        markup_type: markupType,
        extra_percent: payloadExtra,
        tax_rate: payloadTax,
        compare_price_markup: payloadCompare,
        collection_ids: selectedCollections,
        auto_sync: isAdvance ? isAutoSyncEnabled : false
      });

      setSuccessMsg(`✅ ${res.data.message}. Check backend terminal.`);
      setUrl(''); 
      setModalKey(prev => prev + 1); 
      setIsModalOpen(false);
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to connect to backend.';
      setError(msg);
      alert(msg);
    } finally {
      setLoading(false);
    }
  }, [selectedStore, markup, markupType, extraPercent, taxRate, comparePriceMarkup, selectedCollections, isAutoSyncEnabled, isAdvance]);

  const handleBackFromSettings = useCallback(() => {
    setMarkup(localStorage.getItem('global_markup') || '0');
    setMarkupType(localStorage.getItem('global_markup_type') || 'percent');
    setExtraPercent(localStorage.getItem('global_extra_percent') || '0');
    setTaxRate(localStorage.getItem('global_tax_rate') || '0');
    setComparePriceMarkup(localStorage.getItem('global_compare_markup') || '0');
    setActiveTab('dashboard');
    window.history.pushState({}, '', '/');
  }, []);

  const handleTabChange = useCallback((tab) => {
    if (tab === 'manual-sync' && !isAdvance) {
      alert("Manual Sync is an Advance Plan feature. Please upgrade.");
      setActiveTab('billing');
      window.history.replaceState({}, '', '/billing');
      return;
    }

    setActiveTab(tab);
    const pathMap = { dashboard: '/', 'manual-sync': '/manual-sync', settings: '/settings', billing: '/billing' };
    window.history.pushState({}, '', pathMap[tab] || '/');
  }, [isAdvance]);

  if (planLoading) {
    return (
      <div className="h-screen w-full flex flex-col items-center justify-center bg-[#F8F9FA]">
        <Loader2 className="animate-spin text-green-600 mb-4" size={40} />
        <p className="text-gray-500 font-medium">Loading your workspace...</p>
      </div>
    );
  }

  // 🔥 NAYA: Warning Banner Component (Trial aur Limit ke liye)
  const renderBanner = () => {
    // 1. Trial Expired (Red)
    if (isExpired) {
      return (
        <div className="bg-red-600 text-white text-center py-2.5 text-sm font-medium flex justify-center items-center gap-2">
          <ShieldAlert size={18} /> Your trial has expired. Please subscribe to a plan to continue.
        </div>
      );
    }
    // 2. Trial Active (Yellow)
    if (daysLeftInTrial > 0 && !isAdvance) {
      return (
        <div className="bg-yellow-100 text-yellow-800 text-center py-2.5 text-sm font-medium flex justify-center items-center gap-2 border-b border-yellow-200">
          <Clock size={18} /> Your Basic Trial expires in <b>{daysLeftInTrial} days</b>. Upgrade to keep features.
        </div>
      );
    }
    // 3. Product Limit Warning (Orange - 80% crossed)
    if (productCount >= (productLimit * 0.8)) {
      return (
        <div className="bg-orange-100 text-orange-800 text-center py-2.5 text-sm font-medium flex justify-center items-center gap-2 border-b border-orange-200">
          <AlertTriangle size={18} /> You have used {productCount}/{productLimit} product limit. Upgrade for more.
        </div>
      );
    }
    return null;
  };

  return (
    <div className="flex flex-col h-screen bg-[#F8F9FA] font-sans text-gray-800">
      {renderBanner()} {/* 🔥 YEH ADD KARO */}
      
      <main className="flex-1 flex flex-col overflow-y-auto">
        <header className="h-20 bg-white border-b border-gray-200 flex items-center justify-between px-8 shrink-0">
          <div className="flex flex-col">
            <h2 className="text-xl font-bold capitalize">{activeTab.replace('-', ' ')}</h2>
            <p className="text-xs text-gray-500 mt-0.5">
              Overview of your Amazon catalog imports, pricing rules, and real-time sync health.
            </p>
          </div>

          <div className="flex items-center gap-4">
            <span className={`px-3 py-1.5 rounded-full text-xs font-bold ${
              isAdvance ? "bg-purple-100 text-purple-700" : "bg-gray-100 text-gray-600"
            }`}>
              {isAdvance ? "⭐ Advance" : "Basic"}
              {isExpired && " (Expired)"}
            </span>

            {isBasic && !isExpired && (
              <button onClick={() => handleTabChange('billing')} className="bg-gradient-to-r from-purple-600 to-pink-600 text-white text-sm px-4 py-2 rounded-lg font-medium flex items-center gap-1.5 shadow-sm hover:opacity-90 transition">
                <Sparkles size={16} /> Upgrade
              </button>
            )}

            {isExpired && (
              <button onClick={() => handleTabChange('billing')} className="bg-red-600 text-white text-sm px-4 py-2 rounded-lg font-medium flex items-center gap-1.5 shadow-sm hover:bg-red-700 transition">
                <ShieldAlert size={16} /> Subscribe Now
              </button>
            )}

            {isAdvance && (
              <button onClick={() => handleTabChange('manual-sync')} className="border border-gray-300 bg-white text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors shadow-sm">
                View Sync Logs
              </button>
            )}
          </div>
        </header>

        <div className="p-8">
          {activeTab === 'dashboard' && (
            <DashboardView
              url={url} setUrl={setUrl} loading={loading} onSubmit={handleModalImport}
              isAutoSyncEnabled={isAutoSyncEnabled} onToggleAutoSync={handleToggleAutoSync}
              collections={collections} selectedCollections={selectedCollections} setSelectedCollections={setSelectedCollections}
              markup={markup} markupType={markupType} 
              extraPercent={isAdvance ? extraPercent : '0'} 
              taxRate={isAdvance ? taxRate : '0'} 
              comparePriceMarkup={isAdvance ? comparePriceMarkup : '0'}
              API_URL={API_URL} selectedStoreId={selectedStoreId}
              isAdvance={isAdvance}
              isExpired={isExpired}
              productCount={productCount}
              productLimit={productLimit}
            />
          )}

          {activeTab === 'manual-sync' && isAdvance && ( 
            <ManualSync API_URL={API_URL} selectedStoreId={selectedStoreId} isAutoSyncEnabled={isAutoSyncEnabled} onToggleAutoSync={handleToggleAutoSync} />
          )}

          {activeTab === 'settings' && (
            <Settings onBack={handleBackFromSettings} storeId={selectedStoreId} API_URL={API_URL} shopDomain={selectedStore} />
          )}

          {activeTab === 'billing' && <Billing />}
        </div>
      </main>

      <ImportModal
        key={modalKey} isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} onImport={handleModalImport}
        loading={loading} error={error} markup={markup} markupType={markupType} 
        extraPercent={isAdvance ? extraPercent : '0'} 
        taxRate={isAdvance ? taxRate : '0'}
        comparePriceMarkup={isAdvance ? comparePriceMarkup : '0'} 
        collections={collections} selectedCollections={selectedCollections}
        setSelectedCollections={setSelectedCollections} isAutoSyncEnabled={isAutoSyncEnabled} onToggleAutoSync={handleToggleAutoSync}
      />
    </div>
  );
}