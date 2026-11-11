export default function CollectionSelector({ 
  collections, selectedCollections, onToggle, loading 
}) {
  return (
    <div className="lg:col-span-3 bg-white dark:bg-gray-800/50 rounded-2xl p-4 md:p-5 border border-gray-200 dark:border-gray-700 shadow-sm w-full">
      <label className="block text-sm font-bold text-gray-800 dark:text-gray-200 mb-4">
        Add to Collections
      </label>
      <div className="flex flex-wrap gap-2 md:gap-2.5 max-h-40 overflow-y-auto pr-2">
        {collections.length === 0 ? (
          <span className="text-sm text-gray-400 italic">No collections found...</span>
        ) : (
          collections.map(col => (
            <button
              key={col.id}
              onClick={() => onToggle(col.id)}
              disabled={loading}
              className={`px-3 md:px-4 py-1.5 md:py-2 text-xs md:text-sm font-semibold rounded-xl border-2 transition-all duration-200 ${
                selectedCollections.includes(col.id) 
                  ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-500 text-blue-700 dark:text-blue-300 shadow-sm' 
                  : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:border-blue-300 dark:hover:border-gray-600 hover:bg-gray-50'
              }`}
            >
              {col.title}
            </button>
          ))
        )}
      </div>
    </div>
  );
}