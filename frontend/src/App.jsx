// src/App.jsx
import { useState, useEffect } from 'react';
import axios from 'axios';
import { LayoutDashboard, Package, RefreshCw, BarChart2, Settings as SettingsIcon } from 'lucide-react';

import DashboardView from './components/DashboardView';
import Settings from './components/Settings';
import ManualSync from './components/ManualSync';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard'); 
  
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  
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

  const BACKEND_URL = "https://amazon-builder-production.up.railway.app";
  const API_URL = import.meta.env.VITE_API_URL || `${BACKEND_URL}/api/shopify`;

  // URL ke hisaab se tab change
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

  // Stores fetch
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

  // Collections fetch
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
        compare_price_markup: parseFloat(comparePriceMarkup),
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
    setComparePriceMarkup(localStorage.getItem('global_compare_markup') || '0');
    setActiveTab('dashboard');
    window.history.pushState({}, '', '/'); 
  };

  return (
    <div className="flex h-screen bg-[#F8F9FA] font-sans text-gray-800">
      
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col justify-between hidden md:flex">
        <div>
          <div className="p-6 flex items-center gap-3">
            <div className="bg-green-600 text-white p-2 rounded-lg">
              <LayoutDashboard size={20} />
            </div>
            <div>
              <h1 className="font-bold text-sm">Amazon Product</h1>
              <p className="text-xs text-gray-500">Manager</p>
            </div>
          </div>

          <nav className="mt-4 px-3 space-y-1">
            <NavItem 
              icon={<LayoutDashboard size={18} />} 
              label="Dashboard" 
              active={activeTab === 'dashboard'} 
              onClick={() => setActiveTab('dashboard')} 
            />
            <NavItem 
              icon={<RefreshCw size={18} />} 
              label="Manual Sync" 
              active={activeTab === 'manual-sync'} 
              onClick={() => setActiveTab('manual-sync')} 
            />
            <NavItem 
              icon={<SettingsIcon size={18} />} 
              label="Settings" 
              active={activeTab === 'settings'} 
              onClick={() => setActiveTab('settings')} 
            />
          </nav>
        </div>

        <div className="p-4 border-t border-gray-100 space-y-3">
          <div className="flex items-center justify-between text-xs font-medium text-gray-600">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 bg-green-500 rounded-full"></span> Store Connected
            </div>
            <span className="bg-gray-100 px-2 py-0.5 rounded text-gray-500">US</span>
          </div>
          <p className="text-[10px] text-gray-400 truncate px-1">{selectedStore || "No store connected"}</p>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-y-auto">
        {/* Top Header */}
        <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-8 shrink-0">
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold capitalize">{activeTab.replace('-', ' ')}</h2>
          </div>
          <div className="flex items-center gap-3">
             <div className="bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-medium">
               {selectedStore ? selectedStore.split('.')[0] : 'Store'}
             </div>
          </div>
        </header>

        {/* Page Content */}
        <div className="p-8">
          {activeTab === 'dashboard' && (
            <DashboardView 
              API_URL={API_URL}
              selectedStoreId={selectedStoreId}
              url={url} setUrl={setUrl}
              loading={loading} onSubmit={handlePushToShopify}
              stores={stores} selectedStore={selectedStore} setSelectedStore={setSelectedStore}
              collections={collections} selectedCollections={selectedCollections} setSelectedCollections={setSelectedCollections}
              markup={markup} markupType={markupType} extraPercent={extraPercent} taxRate={taxRate}
              error={error} successMsg={successMsg}
            />
          )}
          
          {activeTab === 'manual-sync' && (
            <ManualSync API_URL={API_URL} selectedStoreId={selectedStoreId} />
          )}
          
          {activeTab === 'settings' && (
            <Settings onBack={handleBackFromSettings} storeId={selectedStoreId} />
          )}
        </div>
      </main>
    </div>
  );
}

// Sidebar Navigation Helper
function NavItem({ icon, label, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
        active 
          ? 'bg-gray-100 text-gray-900' 
          : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'
      }`}
    >
      {icon}
      {label}
    </button>
  );
}