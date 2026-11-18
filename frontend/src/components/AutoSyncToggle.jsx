// src/components/AutoSyncToggle.jsx
import { useState, useEffect } from 'react';
import axios from 'axios';
import { Loader2 } from 'lucide-react';

export default function AutoSyncToggle({ API_URL, selectedStoreId }) {
  const [isEnabled, setIsEnabled] = useState(true);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);

  // Status fetch karein page load par
  useEffect(() => {
    const fetchStatus = async () => {
      if (!selectedStoreId) return;
      try {
        const res = await axios.get(`${API_URL}/auto-sync/status?store_id=${selectedStoreId}`);
        setIsEnabled(res.data.enabled);
      } catch (err) {
        console.error("Failed to fetch auto-sync status", err);
      } finally {
        setLoading(false);
      }
    };
    fetchStatus();
  }, [API_URL, selectedStoreId]);

  // Toggle button click handler
  const handleToggle = async () => {
    if (updating) return;
    const newState = !isEnabled;
    setIsEnabled(newState); // UI turant update karein
    setUpdating(true);

    try {
      await axios.post(`${API_URL}/auto-sync/toggle?store_id=${selectedStoreId}`, {
        enabled: newState
      });
    } catch (err) {
      console.error("Failed to update auto-sync", err);
      setIsEnabled(!newState); // Error aane par wapas purani state
      alert("Failed to update Auto-Sync setting.");
    } finally {
      setUpdating(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 flex justify-center items-center h-32">
        <Loader2 className="animate-spin text-gray-400" size={24} />
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 w-full mb-4">
      <div className="flex justify-between items-start mb-2">
        <div>
          <h3 className="text-lg font-bold text-gray-900">Auto-Sync Engine</h3>
        </div>
        <button 
          onClick={handleToggle}
          disabled={updating}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
            isEnabled ? 'bg-[#008060]' : 'bg-gray-300'
          } ${updating ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
            isEnabled ? 'translate-x-6' : 'translate-x-1'
          }`} />
        </button>
      </div>
      
      <p className="text-sm text-gray-500 mb-6 pr-12">
        Automatically monitor Amazon price changes and stock availability in the background.
      </p>

      <div className="border-t border-gray-100 pt-4 flex items-center justify-between">
        <span className="text-sm text-gray-500">Status</span>
        <div className="flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full ${isEnabled ? 'bg-[#008060]' : 'bg-gray-400'}`}></span>
          <span className={`text-sm font-medium ${isEnabled ? 'text-[#008060]' : 'text-gray-500'}`}>
            {isEnabled ? 'Enabled' : 'Disabled'}
          </span>
        </div>
      </div>
    </div>
  );
}