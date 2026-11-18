// src/components/ManualSync.jsx
import { useState, useEffect } from 'react';
import axios from 'axios';
import { RefreshCw, Loader2, Power } from 'lucide-react';
import Loader from './Loader'; // ✅ Loader Import kiya

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
      if (!selectedStoreId) {
        setLoadingStatus(false);
        return;
      }
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
      setMessage("Failed to start sync. Please check backend logs.");
    } finally {
      setSyncing(false);
    }
  };

  // ✅ FIX: Agar data load ho raha hai toh pura page loader dikhayein
  if (loadingStatus) {
    return <Loader message="Loading sync settings..." />;
  }

  return (
    <div className="flex flex-col p-4 max-w-5xl mx-auto space-y-6">
      
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Sync Management</h1>
        <p className="text-sm text-gray-500 mt-1">Manage automated background syncing and trigger manual updates.</p>
      </div>

      {/* ✅ 2 Columns Layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-stretch">
        
        {/* 1. Auto-Sync Toggle Card */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 flex flex-col justify-between h-full">
          <div>
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                  <Power className="text-green-600" size={20} /> Auto-Sync Engine
                </h3>
                <p className="text-sm text-gray-500 mt-2">
                  Automatically monitor Amazon price changes and stock availability in the background.
                </p>
              </div>
              <button 
                onClick={handleToggle}
                disabled={updatingToggle}
                className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors focus:outline-none ${
                  isEnabled ? 'bg-[#008060]' : 'bg-gray-300'
                } ${updatingToggle ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  isEnabled ? 'translate-x-6' : 'translate-x-1'
                }`} />
              </button>
            </div>
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

        {/* 2. Manual Sync Card */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 flex flex-col justify-between h-full text-center">
          <div>
            <div className="mx-auto bg-gray-50 w-16 h-16 rounded-full flex items-center justify-center mb-4 border border-gray-100">
              <RefreshCw size={28} className={syncing ? "animate-spin text-blue-600" : "text-blue-600"} />
            </div>

            <h2 className="text-lg font-bold text-gray-900 mb-2">Manual Price & Inventory Sync</h2>
            <p className="text-sm text-gray-500 mb-4 leading-relaxed">
              Instantly fetch the latest prices and stock from Amazon and update your Shopify store. Bypasses the 2 AM cron job.
            </p>

            <p className="text-xs text-gray-400 mb-6 bg-gray-50 inline-block px-3 py-1 rounded-full border border-gray-100">
              Target Store ID: <span className="text-gray-700 font-mono font-medium">{selectedStoreId || 'Not Connected'}</span>
            </p>
          </div>

          <div>
            <button
              onClick={handleManualSync}
              disabled={syncing || !selectedStoreId}
              className={`w-full py-3 rounded-lg font-bold text-sm transition-all flex items-center justify-center gap-2 ${
                syncing || !selectedStoreId
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-[#008060] hover:bg-[#006e52] text-white shadow-sm'
              }`}
            >
              {syncing ? (
                <>
                  <Loader2 className="animate-spin" size={18} /> Syncing...
                </>
              ) : (
                "Run Manual Sync Now"
              )}
            </button>

            {message && (
              <div className={`mt-4 p-3 rounded-lg text-sm font-medium ${
                message.includes('Failed') ? 'bg-red-50 text-red-600 border border-red-100' : 'bg-green-50 text-green-700 border border-green-100'
              }`}>
                {message}
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}