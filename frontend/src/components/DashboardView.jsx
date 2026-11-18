// src/components/DashboardView.jsx
import { useState, useEffect } from 'react';
import axios from 'axios';
import { Box, CheckCircle2, AlertTriangle, Activity } from 'lucide-react';
import ProductForm from './ProductForm';
import Alerts from './Alerts';

export default function DashboardView({ 
  url, setUrl, loading, onSubmit, 
  stores, selectedStore, setSelectedStore,
  collections, selectedCollections, setSelectedCollections,
  markup, markupType, extraPercent, taxRate,
  error, successMsg,
  API_URL,
  selectedStoreId
}) {
  const [statsData, setStatsData] = useState({
    total_products: 0,
    active_products: 0,
    out_of_stock: 0,
    recent_products: []
  });
  const [fetchingStats, setFetchingStats] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      // ✅ Agar store ID nahi hai, toh wait karein
      if (!selectedStoreId) {
        setFetchingStats(true);
        return;
      }
      
      setFetchingStats(true);
      try {
        const res = await axios.get(`${API_URL}/dashboard-stats?store_id=${selectedStoreId}`);
        setStatsData(res.data);
      } catch (err) {
        console.error("Failed to fetch dashboard stats", err);
      } finally {
        setFetchingStats(false);
      }
    };
    fetchStats();
  }, [API_URL, selectedStoreId]);

  const stats = [
    { 
      title: 'Total Products', 
      value: fetchingStats ? '...' : statsData.total_products.toLocaleString(), 
      sub: 'All time', 
      subColor: 'text-gray-600 bg-gray-100', 
      desc: 'Linked to Shopify catalog', 
      icon: <Box className="text-gray-400" size={20} /> 
    },
    { 
      title: 'Active Products', 
      value: fetchingStats ? '...' : statsData.active_products.toLocaleString(), 
      sub: 'Published', 
      subColor: 'text-green-600 bg-green-50', 
      desc: 'Live on your store', 
      icon: <CheckCircle2 className="text-green-500" size={20} /> 
    },
    { 
      title: 'Out of Stock', 
      value: fetchingStats ? '...' : statsData.out_of_stock.toLocaleString(), 
      sub: 'Auto-zeroed', 
      subColor: 'text-orange-600 bg-orange-50', 
      desc: 'Protected from overselling', 
      icon: <AlertTriangle className="text-orange-400" size={20} /> 
    },
    { 
      title: 'Sync Health', 
      value: '100%', 
      sub: 'Healthy', 
      subColor: 'text-green-700 bg-green-100', 
      desc: 'Auto-sync running', 
      icon: <Activity className="text-green-500" size={20} /> 
    },
  ];

  return (
    <div className="space-y-6">
      
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">Overview of your Amazon catalog imports, pricing rules, and real-time sync health.</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat, i) => (
          <div key={i} className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
            <div className="flex justify-between items-start mb-2">
              <span className="text-sm font-medium text-gray-500">{stat.title}</span>
              {stat.icon}
            </div>
            <div className="flex items-baseline gap-2 mb-1">
              <span className="text-2xl font-bold text-gray-900">{stat.value}</span>
              <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${stat.subColor}`}>{stat.sub}</span>
            </div>
            <p className="text-xs text-gray-400">{stat.desc}</p>
          </div>
        ))}
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Product Form */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4">Import New Product</h3>
          
          <ProductForm 
            url={url} setUrl={setUrl}
            loading={loading} onSubmit={onSubmit}
            stores={stores} selectedStore={selectedStore} setSelectedStore={setSelectedStore}
            collections={collections} selectedCollections={selectedCollections} setSelectedCollections={setSelectedCollections}
            markup={markup} markupType={markupType} extraPercent={extraPercent} taxRate={taxRate}
          />
          
          <div className="mt-4">
            <Alerts error={error} successMsg={successMsg} />
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
            {fetchingStats ? (
              <p className="text-sm text-gray-400">Loading...</p>
            ) : statsData.recent_products.length === 0 ? (
              <p className="text-sm text-gray-400">No recent products.</p>
            ) : (
              statsData.recent_products.map((p) => (
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