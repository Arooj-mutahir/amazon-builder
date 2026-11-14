import { Link as LinkIcon } from 'lucide-react';

export default function UrlStoreInput({ 
  url, setUrl, stores, selectedStore, setSelectedStore, loading 
}) {
  return (
    <div className="flex flex-col md:flex-row gap-4 w-full">
      <div className="flex-1 relative group w-full">
        <LinkIcon className="absolute left-4 top-3.5 w-5 h-5 text-gray-400 group-focus-within:text-blue-500 transition-colors" />
        <input
          type="text"
          placeholder="Paste Amazon Product URL here..."
          className="w-full pl-12 pr-4 py-3.5 bg-gray-50/50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-white rounded-2xl focus:bg-white dark:focus:bg-gray-800 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none transition-all shadow-sm text-sm md:text-base"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          disabled={loading}
        />
      </div>
      
      {/* ✅ FIX: Dropdown tabhi dikhe jab 1 se zyada stores hon */}
      {stores.length > 1 && (
        <select 
          className="w-full md:w-auto px-5 py-3.5 bg-gray-50/50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-2xl text-gray-700 dark:text-gray-200 font-semibold outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all cursor-pointer shadow-sm text-sm md:text-base"
          value={selectedStore}
          onChange={(e) => setSelectedStore(e.target.value)}
          disabled={loading}
        >
          {stores.map((store) => (
            <option key={store.id || store.shop_domain} value={store.shop_domain}>
              {store.shop_domain.split('.')[0]}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}