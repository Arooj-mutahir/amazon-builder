// src/components/ManualSync.jsx
import { useState, useEffect } from 'react';
import axios from 'axios';
import { RefreshCw, Loader2, Power } from 'lucide-react';

export default function ManualSync({ API_URL, selectedStoreId }) {
  // Manual Sync States
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState('');

  // Auto Sync States
  const [isEnabled, setIsEnabled] = useState(true);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [updatingToggle, setUpdatingToggle] = useState(false);

  // Fetch Auto-Sync status on load
  useEffect(() => {
    const fetchAutoSyncStatus = async () => {
      if (!selectedStoreId) return;
      try {
        const res = await axios.get(`${API_URL}/auto-sync/status?store_id=${selectedStoreId}`);
        setIsEnabled(res.data.enabled);
      } catch (err) {
        console.error("Failed to fetch auto-sync status", err);
      } finally {
        setLoadingStatus(false);
      }
    };
    fetchAutoSyncStatus();
  }, [API_URL, selectedStoreId]);

  // Handle Auto-Sync Toggle
  const handleToggle = async () => {
    if (updatingToggle) return;
    const newState = !isEnabled;
    setIsEnabled(newState);
    setUpdatingToggle(true);

    try {
      await axios.post(`${API_URL}/auto-sync/toggle?store_id=${selectedStoreId}`, {
        enabled: newState
      });
    } catch (err) {
      console.error("Failed to update auto-sync", err);
      setIsEnabled(!newState);
      alert("Failed to update Auto-Sync setting.");
    } finally {
      setUpdatingToggle(false);
    }
  };

  // Handle Manual Sync
  const handleManualSync = async () => {
    if (!selectedStoreId) {
      alert("Store ID not found. Please connect a store.");
      return;
    }

    setSyncing(true);
    setMessage('');
    
    try {
      const res = await axios.post(`${API_URL}/manual-sync?store_id=${selectedStoreId}`);
      setMessage(res.data.message || "Sync started successfully!");
    } catch (err) {
      console.error(err);
      setMessage("Failed to start sync. Check backend logs.");
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center p-8 mt-4 space-y-6 max-w-3xl mx-auto">
      
      {/* ✅ 1. Auto-Sync Toggle Card (Yahan add kiya gaya hai) */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 w-full">
        <div className="flex justify-between items-start">
          <div>
            <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
              <Power className="text-green-600" size={20} /> Auto-Sync Engine
            </h3>
            <p className="text-sm text-gray-500 mt-1 pr-6">
              Automatically monitor Amazon price changes and stock availability in the background.
            </p>
          </div>
          {loadingStatus ? (
             <Loader2 className="animate-spin text-gray-400" size={24} />
          ) : (
            <button 
              onClick={handleToggle}
              disabled={updatingToggle}
              className={`relative inline-flex h-7 w-12 shrink-0 items-center rounded-full transition-colors focus:outline-none ${
                isEnabled ? 'bg-[#008060]' : 'bg-gray-300'
              } ${updatingToggle ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <span className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${
                isEnabled ? 'translate-x-6' : 'translate-x-1'
              }`} />
            </button>
          )}
        </div>
        <div className="border-t border-gray-100 pt-4 mt-4 flex items-center justify-between">
          <span className="text-sm font-medium text-gray-500">Status</span>
          <div className="flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${isEnabled ? 'bg-[#008060]' : 'bg-gray-400'}`}></span>
            <span className={`text-sm font-bold ${isEnabled ? 'text-[#008060]' : 'text-gray-500'}`}>
              {isEnabled ? 'Enabled' : 'Disabled'}
            </span>
          </div>
        </div>
      </div>

      {/* 2. Manual Sync Card (Aapki image wala dark card) */}
      <div className="bg-[#1f2937] text-white rounded-2xl shadow-xl w-full p-10 text-center relative overflow-hidden">
        
        <div className="mx-auto bg-[#374151] w-20 h-20 rounded-full flex items-center justify-center mb-6 shadow-inner">
          <RefreshCw size={36} className={syncing ? "animate-spin text-blue-400" : "text-blue-400"} />
        </div>

        <h2 className="text-3xl font-bold mb-4">Manual Price & Inventory Sync</h2>
        <p className="text-gray-300 mb-8 text-base leading-relaxed">
          Click the button below to instantly fetch the latest prices and stock from Amazon and update your Shopify store. (Bypasses the 2 AM cron job).
        </p>

        <p className="text-sm text-gray-400 mb-6">
          Target Store ID: <span className="text-white font-mono">{selectedStoreId || 'Not Connected'}</span>
        </p>

        <button
          onClick={handleManualSync}
          disabled={syncing || !selectedStoreId}
          className={`px-8 py-3 rounded-xl font-bold text-lg transition-all flex items-center justify-center gap-2 mx-auto w-full max-w-xs ${
            syncing || !selectedStoreId
              ? 'bg-blue-800 text-blue-300 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-500 text-white shadow-lg hover:shadow-xl'
          }`}
        >
          {syncing ? (
            <>
              <Loader2 className="animate-spin" size={20} /> Syncing...
            </>
          ) : (
            "Run Manual Sync Now"
          )}
        </button>

        {message && (
          <div className={`mt-6 p-3 rounded-lg text-sm font-medium ${message.includes('Failed') ? 'bg-red-900/50 text-red-200' : 'bg-green-900/50 text-green-200'}`}>
            {message}
          </div>
        )}

      </div>
    </div>
  );
}