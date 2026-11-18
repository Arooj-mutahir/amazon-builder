// src/components/CollectionSelector.jsx
export default function CollectionSelector({ 
  collections, selectedCollections, onToggle, loading, isModal = false 
}) {
  return (
    <div className={isModal ? "" : "bg-white rounded-xl p-4 md:p-5 border border-gray-200 shadow-sm w-full h-full flex flex-col"}>
      <label className="block text-sm font-bold text-gray-800 mb-3">
        Add to Collections
      </label>
      <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto pr-1 content-start">
        {collections.length === 0 ? (
          <span className="text-sm text-gray-400 italic">No collections found...</span>
        ) : (
          collections.map(col => (
            <button
              key={col.id}
              type="button"
              onClick={() => onToggle(col.id)}
              disabled={loading}
              className={`text-xs md:text-sm font-semibold rounded-lg border transition-all duration-200 px-3 py-1.5 ${
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