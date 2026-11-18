// src/components/CollectionSelector.jsx
export default function CollectionSelector({ 
  collections, selectedCollections, onToggle, loading 
}) {
  return (
    <div className="bg-white rounded-xl p-4 md:p-5 border border-gray-200 shadow-sm w-full h-full flex flex-col">
      <label className="block text-sm font-bold text-gray-800 mb-4">
        Add to Collections
      </label>
      <div className="flex flex-wrap gap-2 md:gap-2.5 overflow-y-auto pr-2 flex-1 content-start">
        {collections.length === 0 ? (
          <span className="text-sm text-gray-400 italic">No collections found...</span>
        ) : (
          collections.map(col => (
            <button
              key={col.id}
              onClick={() => onToggle(col.id)}
              disabled={loading}
              className={`px-3 md:px-4 py-1.5 md:py-2 text-xs md:text-sm font-semibold rounded-lg border transition-all duration-200 ${
                selectedCollections.includes(col.id) 
                  ? 'bg-blue-50 border-blue-500 text-blue-700 shadow-sm' 
                  : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300 hover:bg-gray-50'
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