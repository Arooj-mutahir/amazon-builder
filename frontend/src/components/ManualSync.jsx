// frontend/src/components/ManualSync.jsx
import { useState } from 'react';
import axios from 'axios';
import { RefreshCw, CheckCircle, AlertCircle } from 'lucide-react';

// ✅ UPDATED: selectedStoreId prop receive karein
export default function ManualSync({ API_URL, selectedStoreId }) {
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');

  const handleSync = async () => {
    // ✅ Safety check: Agar store ID nahi hai toh error dein
    if (!selectedStoreId) {
      setError("No store connected. Please connect a store first.");
      return;
    }

    setLoading(true);
    setSuccess('');
    setError('');

    try {
      // ✅ UPDATED: store_id body mein bhejein
      const res = await axios.post(`${API_URL}/trigger-sync`, {
        store_id: selectedStoreId
      });
      setSuccess(res.data.message || 'Sync started successfully! Check backend logs.');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start sync.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white/90 dark:bg-gray-900/90 backdrop-blur-sm rounded-3xl shadow-xl p-8 border border-white dark:border-gray-800 w-full max-w-2xl mx-auto text-center mt-10">
      
      <div className="bg-blue-50 dark:bg-blue-900/20 w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-6">
        <RefreshCw className={`w-10 h-10 text-blue-600 dark:text-blue-400 ${loading ? 'animate-spin' : ''}`} />
      </div>

      <h2 className="text-2xl font-extrabold text-gray-900 dark:text-white mb-2">Manual Price & Inventory Sync</h2>
      <p className="text-gray-500 dark:text-gray-400 mb-8 text-sm md:text-base">
        Click the button below to instantly fetch the latest prices and stock from Amazon and update your Shopify store. (Bypasses the 2 AM cron job).
      </p>

      {/* ✅ Optional: Dikhayein kis store ka sync ho raha hai */}
      {selectedStoreId && (
        <p className="text-xs text-gray-400 mb-4">
          Target Store ID: <span className="font-semibold text-blue-500">{selectedStoreId}</span>
        </p>
      )}

      <button
        onClick={handleSync}
        disabled={loading || !selectedStoreId}
        className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3.5 px-8 rounded-2xl transition-all shadow-md disabled:opacity-50 flex items-center justify-center gap-2 mx-auto w-full md:w-auto"
      >
        {loading ? 'Starting Sync...' : 'Run Manual Sync Now'}
      </button>

      {success && (
        <div className="mt-6 p-4 bg-green-50 text-green-700 rounded-xl flex items-center gap-3 justify-center">
          <CheckCircle className="w-5 h-5" /> {success}
        </div>
      )}

      {error && (
        <div className="mt-6 p-4 bg-red-50 text-red-700 rounded-xl flex items-center gap-3 justify-center">
          <AlertCircle className="w-5 h-5" /> {error}
        </div>
      )}
    </div>
  );
}