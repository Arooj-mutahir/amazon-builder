// src/components/DashboardView.jsx
import { useState, useEffect } from 'react';
import axios from 'axios';
import { Box, CheckCircle2, AlertTriangle, Activity } from 'lucide-react';

export default function DashboardView({ 
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

      {/* Recent Products (Full Width) */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h3 className="text-lg font-bold text-gray-900">Recent Products</h3>
            <p className="text-xs text-gray-500">Latest imported products from your connected store</p>
          </div>
        </div>

        <div className="space-y-4">
          {fetchingStats ? (
            <p className="text-sm text-gray-400">Loading products...</p>
          ) : statsData.recent_products.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">No recent products found. Click "Import Products" to add new items.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {statsData.recent_products.map((p) => (
                <div key={p.id} className="flex flex-col p-4 border border-gray-100 rounded-xl hover:bg-gray-50 transition-colors">
                  <div className="flex items-start justify-between mb-3">
                    <div className="w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center shrink-0">
                        <Box className="text-gray-300" size={24} />
                    </div>
                    <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${p.is_available ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-700'}`}>
                      {p.is_available ? 'Active' : 'Out of Stock'}
                    </span>
                  </div>
                  <p className="font-medium text-gray-900 text-sm line-clamp-2">{p.title}</p>
                  <div className="mt-3 flex items-center justify-between">
                     <p className="text-xs text-gray-500">ASIN: {p.asin}</p>
                     <p className="text-sm font-bold text-gray-900">${p.price}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

    </div>
  );
}