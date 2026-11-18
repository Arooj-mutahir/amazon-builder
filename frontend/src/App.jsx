// src/App.jsx
import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Plus, Loader2 } from 'lucide-react'; 

import DashboardView from './components/DashboardView';
import Settings from './components/Settings';
import ManualSync from './components/ManualSync';
import ImportModal from './components/ImportModal';

const BACKEND_URL = "https://amazon-builder-production.up.railway.app";

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [tabLoading, setTabLoading] = useState(false); // ✅ NAYA: Page transition loader

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

  const API_URL = import.meta.env.VITE_API_URL || `${BACKEND_URL}/api/shopify`;

  // URL-based initial tab detection
  useEffect(() => {
    const path = window.location.pathname;
    if (path.includes('settings')) {
      setActiveTab('settings');
    } else if (path.includes('manual-sync')) {
      setActiveTab('manual-sync');
    } else {
      setActiveTab('dashboard');
    }
  }, []);

  // Fetch stores on mount
  useEffect(() => {
    const fetchStores = async () => {
      try {
        const res = await axios.get(`${API_URL}/stores`);
        setStores(res.data);

        if (res.data.length > 0) {
          const urlParams = new URLSearchParams(window.location.search);
          const shopFromUrl = urlParams.get('shop');

          const foundStore = res.data.find(s => s.shop_domain === shopFromUrl) || res.data[0];

          setSelectedStore(foundStore.shop_domain);
          setSelectedStoreId(foundStore.id);
        }
      } catch (err) {
        console.error("Failed to fetch stores", err);
      }
    };
    fetchStores();
  }, [API_URL]);

  // Keep selectedStoreId in sync whenever selectedStore changes
  useEffect(() => {
    if (!selectedStore || stores.length === 0) return;
    const store = stores.find(s => s.shop_domain === selectedStore);
    if (store && store.id !== selectedStoreId) {
      setSelectedStoreId(store.id);
    }
  }, [selectedStore, stores, selectedStoreId]);

  // Fetch collections when store changes; reset selected collections
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
  }, [selectedStore, API_URL]);

  const handleModalImport = useCallback(async (importUrl) => {
    if (!importUrl) {
      setError("Please enter a valid URL");
      return;
    }
    if (!selectedStore) {
      setError("Please connect a Shopify store first");
      return;
    }

    setLoading(true);
    setError('');
    setSuccessMsg('');

    try {
      const res = await axios.post(`${API_URL}/app/add-product`, {
        amazon_url: importUrl,
        shop_domain: selectedStore,
        markup: parseFloat(markup),
        markup_type: markupType,
        extra_percent: parseFloat(extraPercent),
        tax_rate: parseFloat(taxRate),
        compare_price_markup: parseFloat(comparePriceMarkup),
        collection_ids: selectedCollections
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
  }, [API_URL, selectedStore, markup, markupType, extraPercent, taxRate, comparePriceMarkup, selectedCollections]);

  const handleBackFromSettings = useCallback(() => {
    setMarkup(localStorage.getItem('global_markup') || '0');
    setMarkupType(localStorage.getItem('global_markup_type') || 'percent');
    setExtraPercent(localStorage.getItem('global_extra_percent') || '0');
    setTaxRate(localStorage.getItem('global_tax_rate') || '0');
    setComparePriceMarkup(localStorage.getItem('global_compare_markup') || '0');
    
    // ✅ Fix: Back jaate waqt loader lagayein
    setTabLoading(true);
    setTimeout(() => {
      setActiveTab('dashboard');
      window.history.pushState({}, '', '/');
      setTabLoading(false);
    }, 100);
  }, []);

  // ✅ Fix: Tab change karne ke liye naya handler (Loader ke sath)
  const handleTabChange = useCallback((tab) => {
    if (tab === activeTab) return; // Agar wahi tab hai toh kuch na karein

    setTabLoading(true);
    setTimeout(() => {
      setActiveTab(tab);
      const pathMap = {
        dashboard: '/',
        'manual-sync': '/manual-sync',
        settings: '/settings'
      };
      window.history.pushState({}, '', pathMap[tab] || '/');
      setTabLoading(false);
    }, 150); // 150ms ka smooth transition
  }, [activeTab]);

  return (
    <div className="flex flex-col h-screen bg-[#F8F9FA] font-sans text-gray-800">

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-y-auto">
        {/* Top Header */}
        <header className="h-20 bg-white border-b border-gray-200 flex items-center justify-between px-8 shrink-0">
          <div className="flex flex-col">
            <h2 className="text-xl font-bold capitalize">{activeTab.replace('-', ' ')}</h2>
            <p className="text-xs text-gray-500 mt-0.5">
              Overview of your Amazon catalog imports, pricing rules, and real-time sync health.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => handleTabChange('manual-sync')}
              className="border border-gray-300 bg-white text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors shadow-sm"
            >
              View Sync Logs
            </button>

            <button
              onClick={() => setIsModalOpen(true)}
              className="bg-[#008060] hover:bg-[#006e52] text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors shadow-sm"
            >
              <Plus size={16} /> Import Products
            </button>
          </div>
        </header>

        {/* Page Content */}
        <div className="p-8 relative flex-1">
          
          {/* ✅ FIX: Agar Tab Loading hai toh spinner dikhayein */}
          {tabLoading ? (
            <div className="absolute inset-0 flex items-center justify-center bg-[#F8F9FA] z-10">
              <div className="flex flex-col items-center gap-3">
                <Loader2 className="w-8 h-8 animate-spin text-[#008060]" />
                <p className="text-sm text-gray-500 font-medium">Loading page...</p>
              </div>
            </div>
          ) : (
            <>
              {activeTab === 'dashboard' && (
                <DashboardView
                  API_URL={API_URL}
                  selectedStoreId={selectedStoreId}
                  url={url} setUrl={setUrl}
                  loading={loading} onSubmit={handleModalImport}
                  stores={stores} selectedStore={selectedStore} setSelectedStore={setSelectedStore}
                  collections={collections} selectedCollections={selectedCollections} setSelectedCollections={setSelectedCollections}
                  markup={markup} markupType={markupType} extraPercent={extraPercent} taxRate={taxRate}
                  error={error} successMsg={successMsg}
                  onOpenImportModal={() => setIsModalOpen(true)}
                />
              )}

              {activeTab === 'manual-sync' && (
                <ManualSync API_URL={API_URL} selectedStoreId={selectedStoreId} />
              )}

              {activeTab === 'settings' && (
                <Settings 
                  onBack={handleBackFromSettings} 
                  storeId={selectedStoreId} 
                  API_URL={API_URL}
                  shopDomain={selectedStore} 
                />
              )}
            </>
          )}
        </div>
      </main>

      {/* Global Import Modal */}
      <ImportModal
        key={modalKey} 
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onImport={handleModalImport}
        loading={loading}
        error={error}
        markup={markup}
        markupType={markupType}
        extraPercent={extraPercent}
        taxRate={taxRate}
        comparePriceMarkup={comparePriceMarkup}
        collections={collections}
        selectedCollections={selectedCollections}
        setSelectedCollections={setSelectedCollections}
      />
    </div>
  );
}