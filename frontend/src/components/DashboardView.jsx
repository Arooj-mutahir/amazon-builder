// src/components/DashboardView.jsx
import { useState, useEffect } from 'react';
import axios from 'axios';
import { Search, RefreshCw, ExternalLink, Trash2, Plus, Package } from 'lucide-react';
import PricingSummary from './PricingSummary';
import CollectionSelector from './CollectionSelector';

export default function DashboardView({ 
  collections, selectedCollections, setSelectedCollections,
  markup, markupType, extraPercent, taxRate,
  API_URL,
  selectedStoreId,
  onOpenImportModal 
}) {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeFilter, setActiveFilter] = useState('All');

  // ✅ SAARE PRODUCTS FETCH KARNE KA LOGIC
  useEffect(() => {
    const fetchAllProducts = async () => {
      if (!selectedStoreId) {
        setLoading(false);
        return;
      }
      
      setLoading(true);
      try {
        // 🔴 YAHAN APNA ENDPOINT DAALEIN JO SAARE PRODUCTS LAATA HO
        // Misaal ke taur par: /products?store_id=123
        const res = await axios.get(`${API_URL}/products?store_id=${selectedStoreId}`);
        
        // Response format handle karna
        if (Array.isArray(res.data)) {
          setProducts(res.data);
        } else if (res.data && res.data.products) {
          setProducts(res.data.products);
        } else if (res.data && res.data.data) {
          setProducts(res.data.data);
        } else {
          setProducts([]);
        }
      } catch (err) {
        console.error("Failed to fetch all products:", err);
        // Agar /products endpoint nahi hai (404 error), toh fallback ke taur par purana endpoint try karein
        try {
          const fallbackRes = await axios.get(`${API_URL}/dashboard-stats?store_id=${selectedStoreId}`);
          if (fallbackRes.data && fallbackRes.data.recent_products) {
            setProducts(fallbackRes.data.recent_products);
          }
        } catch (fallbackErr) {
          console.error("Fallback fetch also failed:", fallbackErr);
        }
      } finally {
        setLoading(false);
      }
    };
    fetchAllProducts();
  }, [API_URL, selectedStoreId]);

  const handleCollectionToggle = (id) => {
    if (selectedCollections.includes(id)) {
      setSelectedCollections(selectedCollections.filter(cId => cId !== id));
    } else {
      setSelectedCollections([...selectedCollections, id]);
    }
  };

  // Filter aur Search Logic
  const filteredProducts = products.filter(p => {
    const title = p.title || p.name || '';
    const asin = p.asin || '';
    const status = p.is_available ? 'Active' : (p.status || 'Draft');

    const matchesSearch = title.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          asin.toLowerCase().includes(searchQuery.toLowerCase());
    
    if (activeFilter === 'All') return matchesSearch;
    if (activeFilter === 'Active') return matchesSearch && status === 'Active';
    if (activeFilter === 'Out of Stock') return matchesSearch && (status === 'Out of Stock' || p.is_available === false);
    if (activeFilter === 'Draft') return matchesSearch && status === 'Draft';
    return matchesSearch;
  });

  return (
    <div className="space-y-6">
      
      {/* 1. Current Settings Section */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
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

      {/* 2. All Products Section */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        
        {/* Table Header */}
        <div className="p-6 border-b border-gray-200 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-gray-900">All Products</h2>
            <p className="text-sm text-gray-500 mt-1">Manage imported Amazon listings, monitor margins, and trigger individual syncs.</p>
          </div>
          {onOpenImportModal && (
            <button 
              onClick={onOpenImportModal}
              className="bg-[#008060] hover:bg-[#006e52] text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors shadow-sm shrink-0"
            >
              <Plus size={16} /> Import from Amazon
            </button>
          )}
        </div>

        {/* Filters & Search Bar */}
        <div className="p-4 border-b border-gray-200 flex flex-col md:flex-row justify-between items-center gap-4 bg-gray-50/50">
          <div className="flex items-center gap-2 overflow-x-auto w-full md:w-auto pb-2 md:pb-0">
            {['All', 'Active', 'Out of Stock', 'Draft'].map(filter => (
              <button
                key={filter}
                onClick={() => setActiveFilter(filter)}
                className={`px-4 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                  activeFilter === filter 
                    ? 'bg-gray-200/80 text-gray-900' 
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                {/* Total count show karne ke liye logic */}
                {filter} {filter === 'All' && products.length > 0 ? products.length : ''}
              </button>
            ))}
          </div>

          <div className="relative w-full md:w-72">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
            <input 
              type="text" 
              placeholder="Search by title or ASIN..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
            />
          </div>
        </div>

        {/* Table List */}
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                <th className="p-4 w-12 text-center">
                  <input type="checkbox" className="rounded border-gray-300" />
                </th>
                <th className="p-4 font-semibold">Product</th>
                <th className="p-4 font-semibold">ASIN</th>
                <th className="p-4 font-semibold">Amazon Price</th>
                <th className="p-4 font-semibold">Shopify Price</th>
                <th className="p-4 font-semibold">Stock</th>
                <th className="p-4 font-semibold">Status</th>
                <th className="p-4 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                <tr>
                  <td colSpan="8" className="p-8 text-center text-gray-500">Loading products...</td>
                </tr>
              ) : filteredProducts.length === 0 ? (
                <tr>
                  <td colSpan="8" className="p-12 text-center">
                    <div className="flex flex-col items-center justify-center text-gray-500 w-full">
                      <Package size={40} className="text-gray-300 mb-3" />
                      <p className="text-base font-medium">No products found for this store.</p>
                      {searchQuery || activeFilter !== 'All' ? (
                        <p className="text-sm text-gray-400 mt-1">Try adjusting your search or filters.</p>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ) : (
                filteredProducts.map((product) => {
                  // Fallbacks handle kiye gaye hain
                  const title = product.title || product.name || 'Unknown Product';
                  const asin = product.asin || 'N/A';
                  const amazonPrice = product.amazon_price || product.price || '0.00';
                  const shopifyPrice = product.shopify_price || product.price || '0.00';
                  const stock = product.stock !== undefined ? product.stock : (product.is_available ? 10 : 0);
                  const isActive = product.is_available !== undefined ? product.is_available : (product.status === 'Active');
                  const statusText = isActive ? 'Active' : (stock === 0 ? 'Out of Stock' : 'Draft');

                  return (
                    <tr key={product.id || product.asin} className="hover:bg-gray-50/50 transition-colors group">
                      <td className="p-4 text-center">
                        <input type="checkbox" className="rounded border-gray-300" />
                      </td>
                      <td className="p-4">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center shrink-0 border border-gray-200">
                            {product.image ? (
                              <img src={product.image} alt="" className="w-full h-full object-cover rounded-lg" />
                            ) : (
                              <Package size={20} className="text-gray-400" />
                            )}
                          </div>
                          <div>
                            <p className="font-medium text-gray-900 text-sm max-w-[250px] truncate" title={title}>
                              {title}
                            </p>
                            <p className="text-xs text-gray-500 mt-0.5">
                              Auto-Sync {product.auto_sync !== false ? 'ON' : 'OFF'}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="p-4">
                        <span className="bg-gray-100 text-gray-600 text-xs px-2 py-1 rounded border border-gray-200 font-mono">
                          {asin}
                        </span>
                      </td>
                      <td className="p-4 text-sm text-gray-600">
                        ${amazonPrice}
                      </td>
                      <td className="p-4 text-sm font-semibold text-gray-900">
                        ${shopifyPrice}
                      </td>
                      <td className="p-4 text-sm">
                        <span className={stock === 0 ? 'text-red-500 font-medium' : 'text-gray-700'}>
                          {stock} in stock
                        </span>
                      </td>
                      <td className="p-4">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold
                          ${statusText === 'Active' ? 'bg-green-100 text-green-700' : 
                            statusText === 'Out of Stock' ? 'bg-red-100 text-red-700' : 
                            'bg-blue-100 text-blue-700'}`}
                        >
                          <span className={`w-1.5 h-1.5 rounded-full ${statusText === 'Active' ? 'bg-green-500' : statusText === 'Out of Stock' ? 'bg-red-500' : 'bg-blue-500'}`}></span>
                          {statusText}
                        </span>
                      </td>
                      <td className="p-4">
                        <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button className="p-1.5 text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded border border-transparent hover:border-gray-200 transition-all" title="Sync Product">
                            <RefreshCw size={16} />
                          </button>
                          <button className="p-1.5 text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded border border-transparent hover:border-gray-200 transition-all" title="View on Shopify">
                            <ExternalLink size={16} />
                          </button>
                          <button className="p-1.5 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded border border-transparent hover:border-red-200 transition-all" title="Delete">
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}