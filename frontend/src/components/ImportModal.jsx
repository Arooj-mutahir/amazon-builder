// src/components/ImportModal.jsx
import { useState } from 'react';
import { X, Plus } from 'lucide-react';
import CollectionSelector from './CollectionSelector'; // ✅ Import kiya

export default function ImportModal({ 
  isOpen, 
  onClose, 
  onImport, 
  loading,
  markup,
  markupType,
  extraPercent,
  taxRate,
  // ✅ Collections ke props receive karein
  collections = [],
  selectedCollections = [],
  setSelectedCollections,
  isAutoSyncEnabled,
  onToggleAutoSync
}) {
  const [url, setUrl] = useState('');

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (url.trim()) {
      onImport(url, isAutoSyncEnabled);
    }
  };

  // Collection toggle function
  const handleCollectionToggle = (id) => {
    if (selectedCollections.includes(id)) {
      setSelectedCollections(selectedCollections.filter(cId => cId !== id));
    } else {
      setSelectedCollections([...selectedCollections, id]);
    }
  };

  const getPricingRuleText = () => {
    let text = "";
    if (markupType === 'percent') text = `+${markup}% Markup`;
    else if (markupType === 'fixed') text = `+$${markup} Fixed`;
    else if (markupType === 'both') text = `+$${markup} Fixed & +${extraPercent}% Extra`;
    
    if (taxRate > 0) text += ` | +${taxRate}% Tax`;
    return text || "No markup applied";
  };

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="flex justify-between items-center p-5 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <div className="bg-green-100 p-1.5 rounded-lg text-green-700">
              <Plus size={18} />
            </div>
            <h2 className="text-lg font-bold text-gray-900">Import from Amazon</h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700">
            <X size={20} />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-5 space-y-5 max-h-[80vh] overflow-y-auto">
          
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Amazon Product URL or ASIN(s)
            </label>
            <textarea
              rows="2"
              placeholder="e.g. https://www.amazon.com/dp/B0BSHF7WHW or B0BSHF7WHW"
              className="w-full p-3 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-green-500 outline-none resize-none"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            ></textarea>
            <p className="text-xs text-gray-500 mt-1">Supports single URLs or comma-separated ASINs.</p>
          </div>

          {/* ✅ NAYA: Collections Selector (URL ke theek neeche) */}
          <div className="border border-gray-200 rounded-lg p-4 bg-gray-50/50">
            <CollectionSelector 
              collections={collections}
              selectedCollections={selectedCollections}
              onToggle={handleCollectionToggle}
              loading={loading}
              isModal={true} // ✅ Isko compact dikhane ke liye
            />
          </div>

          {/* Auto-Sync Toggle */}
          <div className="w-full bg-gray-50 border border-gray-200 rounded-lg p-4 flex justify-between items-center">
            <div>
              <p className="text-sm font-semibold text-gray-800">Auto-Sync</p>
              <p className="text-xs text-gray-500">Price & stock tracking</p>
            </div>
            <div 
              onClick={onToggleAutoSync}
              className={`w-10 h-5 rounded-full cursor-pointer relative transition-colors ${
                isAutoSyncEnabled ? 'bg-[#008060]' : 'bg-gray-300'
              }`}
            >
              <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full transition-transform ${
                isAutoSyncEnabled ? 'left-5' : 'left-0.5'
              }`}></div>
            </div>
          </div>

          {/* Applied Pricing Rule */}
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 flex justify-between items-center text-sm">
            <span className="text-gray-600">Applied Pricing Rule:</span>
            <span className="font-semibold text-gray-900">{getPricingRuleText()}</span>
          </div>

          {/* Footer Buttons */}
          <div className="flex justify-end gap-3 pt-4 border-t border-gray-100">
            <button type="button" onClick={onClose} className="px-5 py-2.5 text-sm font-medium border border-gray-200 rounded-lg text-gray-700 hover:bg-gray-50">
              Cancel
            </button>
            <button type="submit" disabled={loading || !url.trim()} className="px-5 py-2.5 text-sm font-medium bg-[#008060] hover:bg-[#006e52] text-white rounded-lg disabled:opacity-50">
              {loading ? 'Importing...' : 'Import Product'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}