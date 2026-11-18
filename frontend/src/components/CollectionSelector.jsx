// src/components/CollectionSelector.jsx
export default function CollectionSelector({ 
  collections, selectedCollections, onToggle, loading, isModal = false 
}) {
  return (
    <div className={`bg-white w-full h-full flex flex-col ${isModal ? '' : 'rounded-xl p-4 md:p-5 border border-gray-200 shadow-sm'}`}>
      <label className={`block font-bold text-gray-800 ${isModal ? 'text-sm mb-3' : 'text-sm mb-4'}`}>
        Add to Collections
      </label>
      <div className={`flex flex-wrap gap-2 ${isModal ? 'max-h-32' : 'md:gap-2.5 flex-1'} overflow-y-auto pr-2 content-start`}>
        {collections.length === 0 ? (
          <span className="text-sm text-gray-400 italic">No collections found...</span>
        ) : (
          collections.map(col => (
            <button
              key={col.id}
              type="button" // ✅ Form submit hone se rokne ke liye
              onClick={() => onToggle(col.id)}
              disabled={loading}
              className={`text-xs md:text-sm font-semibold rounded-lg border transition-all duration-200 ${
                isModal ? 'px-3 py-1.5' : 'px-3 md:px-4 py-1.5 md:py-2'
              } ${
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