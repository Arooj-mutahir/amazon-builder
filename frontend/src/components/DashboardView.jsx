// src/components/DashboardView.jsx
import { useState, useEffect } from 'react';
import axios from 'axios';
import { Search, RefreshCw, ExternalLink, Trash2, Plus, Package, Loader2, AlertTriangle } from 'lucide-react';
import CollectionSelector from './CollectionSelector';

export default function DashboardView({ 
  url, setUrl, loading, onSubmit,
  collections, selectedCollections, setSelectedCollections,
  markup, markupType, extraPercent, taxRate,
  isAutoSyncEnabled, onToggleAutoSync,
  API_URL,
  selectedStoreId,
  isAdvance,
  isExpired,
  productCount = 0,
  productLimit = 1000,
}) {
  const [products, setProducts] = useState([]);
  const [fetchingProducts, setFetchingProducts] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [activeFilter, setActiveFilter] = useState('All');

  // ✅ Fetch Function (Bahar nikal diya taaki sync/delete ke baad refresh ho sake)
  const fetchAllProducts = async () => {
    if (!selectedStoreId) {
      setFetchingProducts(false);
      return;
    }
    setFetchingProducts(true);
    setError('');
    try {
      const res = await axios.get(`${API_URL}/products?store_id=${selectedStoreId}`);
      if (Array.isArray(res.data)) setProducts(res.data);
      else if (res.data && res.data.products) setProducts(res.data.products);
      else setProducts([]);
    } catch (err) {
      console.error("Failed to fetch all products:", err);
      setError("Products fetch karne mein error aaya. Backend server check karein.");
    } finally {
      setFetchingProducts(false);
    }
  };

  useEffect(() => {
    fetchAllProducts();
  }, [API_URL, selectedStoreId]);

  // 🔥 1. SYNC FUNCTION
  const handleSync = async (product) => {
    if (!product.asin && !product.id) return alert("Invalid product data.");
    
    try {
      await axios.post(`${API_URL}/app/sync-single-product`, {
        store_id: selectedStoreId,
        asin: product.asin,
        product_id: product.id
      });
      alert(`Sync started for ${product.asin || product.title}. Check terminal.`);
      // Optional: 2 second baad refresh karein
      setTimeout(fetchAllProducts, 2000);
    } catch (err) {
      console.error("Sync Error:", err);
      alert(err.response?.data?.detail || "Sync failed. Check backend logs.");
    }
  };

  // 🔥 2. VIEW ON SHOPIFY FUNCTION
  const handleViewOnShopify = (product) => {
    if (!product.shopify_product_id) {
      alert("Shopify Product ID not found for this item.");
      return;
    }
    // GID format se numeric ID nikaalein: gid://shopify/Product/12345 -> 12345
    const numericId = product.shopify_product_id.split('/').pop();
    
    // Store ka sahi handle yahan daalein (Aap chaho toh local storage se le sakte hain)
    const storeHandle = window.location.pathname.split('/')[1] || "YOUR_STORE_HANDLE"; 
    
    window.open(`https://admin.shopify.com/store/${storeHandle}/products/${numericId}`, '_blank');
  };

  // 🔥 3. DELETE FUNCTION
  const handleDelete = async (product) => {
    if (!window.confirm(`Are you sure you want to delete "${product.title}"?`)) return;
    
    try {
      await axios.delete(`${API_URL}/products/${product.id}?store_id=${selectedStoreId}`);
      alert("Product deleted successfully.");
      fetchAllProducts(); // List refresh
    } catch (err) {
      console.error("Delete Error:", err);
      alert(err.response?.data?.detail || "Delete failed. Check backend logs.");
    }
  };

  const handleCollectionToggle = (id) => {
    if (selectedCollections.includes(id)) {
      setSelectedCollections(selectedCollections.filter(cId => cId !== id));
    } else {
      setSelectedCollections([...selectedCollections, id]);
    }
  };

  const handleDashboardImport = (e) => {
    e.preventDefault();
    if (isExpired) return alert("Your trial has expired. Please subscribe to a plan to import products.");
    if (productCount >= productLimit) return alert(`Limit reached (${productLimit}). Upgrade to Advance plan.`);
    if (url.trim()) onSubmit(url); 
  };

  const getPricingRuleText = () => {
    let text = "";
    if (markupType === 'percent') text = `+${markup}% Markup`;
    else if (markupType === 'fixed') text = `+$${markup} Fixed`;
    else if (markupType === 'both') text = `+$${markup} Fixed & +${extraPercent}% Extra`;
    if (taxRate > 0) text += ` | +${taxRate}% Tax`;
    return text || "No markup applied";
  };

  const filteredProducts = products.filter(p => {
    const title = p.title || '';
    const asin = p.asin || '';
    const statusText = p.is_available ? 'Active' : (p.status || 'Out of Stock');
    const matchesSearch = title.toLowerCase().includes(searchQuery.toLowerCase()) || asin.toLowerCase().includes(searchQuery.toLowerCase());
    
    if (activeFilter === 'All') return matchesSearch;
    if (activeFilter === 'Active') return matchesSearch && statusText === 'Active';
    if (activeFilter === 'Out of Stock') return matchesSearch && statusText === 'Out of Stock';
    if (activeFilter === 'Draft') return matchesSearch && statusText === 'Draft';
    return matchesSearch;
  });

  const usagePercent = Math.min(100, (productCount / productLimit) * 100);

  return (
    <div className="space-y-6">
      {/* 1. PRODUCT USAGE BAR */}
      {productCount > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 w-full max-w-3xl mx-auto">
          <div className="flex justify-between items-center mb-2 text-sm">
            <span className="font-semibold text-gray-700">Product Usage ({isAdvance ? 'Advance' : 'Basic'} Plan)</span>
            <span className={`font-bold ${usagePercent > 90 ? 'text-red-600' : 'text-gray-600'}`}>
              {productCount} / {productLimit}
            </span>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-2.5">
            <div className={`h-2.5 rounded-full transition-all ${usagePercent > 90 ? 'bg-red-500' : usagePercent > 75 ? 'bg-orange-400' : 'bg-green-500'}`} style={{ width: `${usagePercent}%` }}></div>
          </div>
        </div>
      )}

      {/* 2. INLINE IMPORT FORM */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 w-full max-w-3xl mx-auto relative overflow-hidden">
        {isExpired && (
          <div className="absolute inset-0 bg-white/70 backdrop-blur-sm z-10 flex flex-col items-center justify-center rounded-xl">
            <AlertTriangle className="text-red-500 mb-2" size={32} />
            <p className="font-bold text-gray-800">Your trial has expired</p>
            <p className="text-sm text-gray-500">Please subscribe to a plan to continue importing.</p>
          </div>
        )}

        <form onSubmit={handleDashboardImport} className="space-y-5">
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">Amazon Product URL or ASIN(s)</label>
            <textarea
              rows="2"
              placeholder="e.g. https://www.amazon.com/dp/B0BSHF7WHW or B0BSHF7WHW"
              className="w-full p-3 bg-white border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-green-500 outline-none resize-none"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              disabled={loading || isExpired}
            />
            <p className="text-xs text-gray-500 mt-1">Supports single URLs or comma-separated ASINs.</p>
          </div>

          <div className="border border-gray-200 rounded-lg p-4 bg-gray-50/50">
            <CollectionSelector 
              collections={collections}
              selectedCollections={selectedCollections}
              onToggle={handleCollectionToggle}
              loading={loading}
              isModal={true}
            />
          </div>

          {isAdvance && (
            <div className="w-full bg-gray-50 border border-gray-200 rounded-lg p-4 flex justify-between items-center">
              <div>
                <p className="text-sm font-semibold text-gray-800">Auto-Sync</p>
                <p className="text-xs text-gray-500">Price & stock tracking</p>
              </div>
              <button 
                type="button"
                onClick={onToggleAutoSync}
                disabled={loading || isExpired}
                className={`w-10 h-5 rounded-full relative transition-colors ${isAutoSyncEnabled ? 'bg-[#008060]' : 'bg-gray-300'}`}
              >
                <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full transition-transform ${isAutoSyncEnabled ? 'left-5' : 'left-0.5'}`}></div>
              </button>
            </div>
          )}

          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 flex justify-between items-center text-sm">
            <span className="text-gray-600">Applied Pricing Rule:</span>
            <span className="font-semibold text-gray-900">{getPricingRuleText()}</span>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-100">
            <button 
              type="submit"
              disabled={loading || !url.trim() || isExpired || productCount >= productLimit}
              className="px-5 py-2.5 text-sm font-medium bg-[#008060] hover:bg-[#006e52] text-white rounded-lg flex items-center gap-2 disabled:opacity-50"
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
              {loading ? 'Importing...' : productCount >= productLimit ? 'Limit Reached' : 'Import Product'}
            </button>
          </div>
        </form>
      </div>

      {/* 3. PRODUCTS TABLE SECTION */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="p-6 border-b border-gray-200 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-gray-900">All Products</h2>
            <p className="text-sm text-gray-500 mt-1">Showing {products.length} products from the database.</p>
          </div>
        </div>

        <div className="p-4 border-b border-gray-200 flex flex-col md:flex-row justify-between items-center gap-4 bg-gray-50/50">
          <div className="flex items-center gap-2 overflow-x-auto w-full md:w-auto pb-2 md:pb-0">
            {['All', 'Active', 'Out of Stock', 'Draft'].map(filter => (
              <button
                key={filter}
                onClick={() => setActiveFilter(filter)}
                className={`px-4 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                  activeFilter === filter ? 'bg-gray-200/80 text-gray-900' : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                {filter}
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

        {error && <div className="p-4 bg-red-50 text-red-600 text-sm border-b border-red-100">{error}</div>}

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                <th className="p-4 w-12 text-center"><input type="checkbox" className="rounded border-gray-300" /></th>
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
              {fetchingProducts ? (
                <tr>
                  <td colSpan="8" className="p-12 text-center">
                    <div className="flex flex-col items-center justify-center text-gray-500 w-full">
                      <Loader2 className="animate-spin text-green-600 mb-3" size={32} />
                      <p className="text-base font-medium">Fetching products...</p>
                    </div>
                  </td>
                </tr>
              ) : filteredProducts.length === 0 ? (
                <tr>
                  <td colSpan="8" className="p-12 text-center">
                    <div className="flex flex-col items-center justify-center text-gray-500 w-full">
                      <Package size={40} className="text-gray-300 mb-3" />
                      <p className="text-base font-medium">No products found.</p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredProducts.map((product) => {
                  const title = product.title || 'Unknown Product';
                  const asin = product.asin || 'N/A';
                  const amazonPrice = product.amazon_price || '0.00';
                  const shopifyPrice = product.shopify_price || '0.00';
                  const stock = product.stock !== undefined ? product.stock : (product.is_available ? 10 : 0);
                  const isActive = product.is_available !== undefined ? product.is_available : (product.status === 'Active');
                  const statusText = isActive ? 'Active' : (stock === 0 ? 'Out of Stock' : 'Draft');

                  return (
                    <tr key={product.id || product.asin} className="hover:bg-gray-50/50 transition-colors group">
                      <td className="p-4 text-center"><input type="checkbox" className="rounded border-gray-300" /></td>
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
                            <p className="font-medium text-gray-900 text-sm max-w-[250px] truncate" title={title}>{title}</p>
                            {isAdvance && (
                              <p className="text-xs text-gray-500 mt-0.5">Auto-Sync {product.auto_sync !== false ? 'ON' : 'OFF'}</p>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="p-4"><span className="bg-gray-100 text-gray-600 text-xs px-2 py-1 rounded border border-gray-200 font-mono">{asin}</span></td>
                      <td className="p-4 text-sm text-gray-600">${amazonPrice}</td>
                      <td className="p-4 text-sm font-semibold text-gray-900">${shopifyPrice}</td>
                      <td className="p-4 text-sm">
                        <span className={stock === 0 ? 'text-red-500 font-medium' : 'text-gray-700'}>{stock} in stock</span>
                      </td>
                      <td className="p-4">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold
                          ${statusText === 'Active' ? 'bg-green-100 text-green-700' : 
                            statusText === 'Out of Stock' ? 'bg-red-100 text-red-700' : 
                            'bg-blue-100 text-blue-700'}`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${statusText === 'Active' ? 'bg-green-500' : statusText === 'Out of Stock' ? 'bg-red-500' : 'bg-blue-500'}`}></span>
                          {statusText}
                        </span>
                      </td>
                      <td className="p-4">
                        <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          
                          {/* 🔥 SYNC BUTTON */}
                          <button 
                            onClick={() => handleSync(product)}
                            className="p-1.5 text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded border border-transparent hover:border-gray-200 transition-all" 
                            title="Sync Product"
                          >
                            <RefreshCw size={16} />
                          </button>

                          {/* 🔥 EXTERNAL LINK BUTTON */}
                          <button 
                            onClick={() => handleViewOnShopify(product)}
                            className="p-1.5 text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded border border-transparent hover:border-gray-200 transition-all" 
                            title="View on Shopify"
                          >
                            <ExternalLink size={16} />
                          </button>

                          {/* 🔥 DELETE BUTTON */}
                          <button 
                            onClick={() => handleDelete(product)}
                            className="p-1.5 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded border border-transparent hover:border-red-200 transition-all" 
                            title="Delete"
                          >
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