// src/components/DashboardView.jsx
import { useState, useEffect } from 'react';
import axios from 'axios';
import PricingSummary from './PricingSummary';
import CollectionSelector from './CollectionSelector';

export default function DashboardView({ 
  collections, selectedCollections, setSelectedCollections,
  markup, markupType, extraPercent, taxRate,
  API_URL,
  selectedStoreId
}) {
  // Recent products ke liye state
  const [recentProducts, setRecentProducts] = useState([]);
  const [fetchingRecent, setFetchingRecent] = useState(true);

  useEffect(() => {
    const fetchRecentProducts = async () => {
      if (!selectedStoreId) {
        setFetchingRecent(false);
        return;
      }
      
      setFetchingRecent(true);
      try {
        // Humne yahan dashboard-stats ki jagah direct data fetch kiya hai (ya aap apna endpoint use kar sakte hain)
        const res = await axios.get(`${API_URL}/dashboard-stats?store_id=${selectedStoreId}`);
        if (res.data && res.data.recent_products) {
          setRecentProducts(res.data.recent_products);
        }
      } catch (err) {
        console.error("Failed to fetch recent products", err);
      } finally {
        setFetchingRecent(false);
      }
    };
    fetchRecentProducts();
  }, [API_URL, selectedStoreId]);

  const handleCollectionToggle = (id) => {
    if (selectedCollections.includes(id)) {
      setSelectedCollections(selectedCollections.filter(cId => cId !== id));
    } else {
      setSelectedCollections([...selectedCollections, id]);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">Overview of your Amazon catalog imports, pricing rules, and real-time sync health.</p>
      </div>

      {/* Main Grid (Bina Stats Cards ke) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Active Pricing & Collections */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-6">Current Settings</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-stretch">
            <PricingSummary 
              markup={markup} 
              markupType={markupType} 
              extraPercent={extraPercent} 
              taxRate={taxRate} 
            />
            
            <CollectionSelector 
              collections={collections}
              selectedCollections={selectedCollections}
              onToggle={handleCollectionToggle}
              loading={false}
            />
          </div>
        </div>

        {/* Recent Activity */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <div className="flex justify-between items-center mb-6">
            <div>
              <h3 className="text-lg font-bold text-gray-900">Recent Products</h3>
              <p className="text-xs text-gray-500">Latest imported products</p>
            </div>
          </div>

          <div className="space-y-4">
            {fetchingRecent ? (
              <p className="text-sm text-gray-400">Loading...</p>
            ) : recentProducts.length === 0 ? (
              <p className="text-sm text-gray-400">No recent products.</p>
            ) : (
              recentProducts.map((p) => (
                <div key={p.id} className="flex items-start justify-between py-3 border-b border-gray-50 last:border-0">
                  <div className="overflow-hidden">
                    <p className="font-medium text-gray-900 text-sm truncate">{p.title}</p>
                    <p className="text-xs text-gray-500 mt-1">ASIN: {p.asin}</p>
                  </div>
                  <div className="text-right shrink-0 ml-4">
                    <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${p.is_available ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-700'}`}>
                      {p.is_available ? 'Active' : 'Out of Stock'}
                    </span>
                    <p className="text-xs text-gray-400 mt-2">${p.price}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

      </div>

    </div>
  );
}