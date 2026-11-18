// src/components/ProductsView.jsx
import { useState } from 'react';
import { Search, RefreshCw, ExternalLink, Trash2, Plus } from 'lucide-react';

export default function ProductsView({ 
  onOpenImportModal,
  statsData,
  fetchingStats
}) {
  const [searchTerm, setSearchTerm] = useState('');

  // Dummy products for UI (Aap inhe API se fetch kar sakte hain)
  const products = statsData.recent_products || [];

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">All Products</h1>
          <p className="text-sm text-gray-500 mt-1">Manage imported Amazon listings, monitor margins, and trigger individual syncs.</p>
        </div>
        
        <button 
          onClick={onOpenImportModal}
          className="bg-[#008060] hover:bg-[#006e52] text-white px-4 py-2.5 rounded-lg text-sm font-medium flex items-center gap-2 shadow-sm transition-colors"
        >
          <Plus size={16} /> Import from Amazon
        </button>
      </div>

      {/* Filters & Search */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
        <div className="p-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
           <div className="flex gap-4 text-sm font-medium text-gray-500">
              <button className="text-gray-900 border-b-2 border-green-600 pb-2">All {products.length}</button>
              <button className="hover:text-gray-900 pb-2">Active</button>
              <button className="hover:text-gray-900 pb-2">Out of Stock</button>
           </div>
           
           <div className="relative w-64">
             <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
             <input 
               type="text" 
               placeholder="Search by title or ASIN..." 
               className="w-full pl-9 pr-4 py-2 bg-white border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-green-500 outline-none"
               value={searchTerm}
               onChange={(e) => setSearchTerm(e.target.value)}
             />
           </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                <th className="p-4 w-10"><input type="checkbox" className="rounded border-gray-300" /></th>
                <th className="p-4">Product</th>
                <th className="p-4">Shopify Price</th>
                <th className="p-4">Stock</th>
                <th className="p-4">Status</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {fetchingStats ? (
                <tr><td colSpan="6" className="p-8 text-center text-gray-500">Loading products...</td></tr>
              ) : products.length === 0 ? (
                <tr><td colSpan="6" className="p-8 text-center text-gray-500">No products found. Import from Amazon to get started.</td></tr>
              ) : (
                products.map((p) => (
                  <tr key={p.id} className="hover:bg-gray-50/50 transition-colors">
                    <td className="p-4"><input type="checkbox" className="rounded border-gray-300" /></td>
                    <td className="p-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center shrink-0">
                           {/* Placeholder Image */}
                           <span className="text-gray-400 text-xs">IMG</span>
                        </div>
                        <div>
                          <p className="font-medium text-sm text-gray-900 line-clamp-1">{p.title}</p>
                          <p className="text-xs text-gray-500 mt-0.5">ASIN: {p.asin}</p>
                        </div>
                      </div>
                    </td>
                    <td className="p-4 font-medium text-sm text-gray-900">${p.price}</td>
                    <td className="p-4 text-sm text-gray-600">{p.is_available ? '100 in stock' : '0 in stock'}</td>
                    <td className="p-4">
                      <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${p.is_available ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                        {p.is_available ? 'Active' : 'Out of Stock'}
                      </span>
                    </td>
                    <td className="p-4">
                      <div className="flex justify-end gap-2 text-gray-400">
                        <button className="p-1.5 hover:bg-gray-200 rounded"><RefreshCw size={16} /></button>
                        <button className="p-1.5 hover:bg-gray-200 rounded"><ExternalLink size={16} /></button>
                        <button className="p-1.5 hover:bg-red-50 hover:text-red-500 rounded"><Trash2 size={16} /></button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}