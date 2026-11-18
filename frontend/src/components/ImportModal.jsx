// src/components/ImportModal.jsx
import { useState } from 'react';
import { X, Plus } from 'lucide-react';

export default function ImportModal({ 
  isOpen, 
  onClose, 
  onImport, 
  loading,
  markup,
  markupType,
  extraPercent,
  taxRate
}) {
  const [url, setUrl] = useState('');
  const [autoSync, setAutoSync] = useState(true);

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (url.trim()) {
      onImport(url, autoSync);
    }
  };

  // Display string for pricing rule
  const getPricingRuleText = () => {
    let text = "";
    if (markupType === 'percent') {
      text = `+${markup}% Markup`;
    } else if (markupType === 'fixed') {
      text = `+$${markup} Fixed Markup`;
    } else if (markupType === 'both') {
      text = `+$${markup} Fixed & +${extraPercent}% Extra`;
    }
    if (taxRate > 0) {
      text += ` | +${taxRate}% Tax`;
    }
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
        <form onSubmit={handleSubmit} className="p-5 space-y-5">
          
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Amazon Product URL or ASIN(s)
            </label>
            <textarea
              rows="3"
              placeholder="e.g. https://www.amazon.com/dp/B0BSHF7WHW or B0BSHF7WHW"
              className="w-full p-3 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-green-500 outline-none resize-none"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            ></textarea>
            <div className="mt-2">
              <p className="text-xs text-gray-500">Supports single URLs or comma-separated ASINs.</p>
            </div>
          </div>

          {/* Removed Default Shopify Status Dropdown, Centered Auto-Sync Toggle */}
          <div className="w-full bg-gray-50 border border-gray-200 rounded-lg p-4 flex justify-between items-center">
            <div>
              <p className="text-sm font-semibold text-gray-800">Auto-Sync</p>
              <p className="text-xs text-gray-500">Price & stock tracking</p>
            </div>
            <div 
              onClick={() => setAutoSync(!autoSync)}
              className={`w-10 h-5 rounded-full cursor-pointer relative transition-colors ${autoSync ? 'bg-green-600' : 'bg-gray-300'}`}
            >
              <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full transition-transform ${autoSync ? 'left-5' : 'left-0.5'}`}></div>
            </div>
          </div>

          {/* Applied Pricing Rule (Dynamic based on user settings) */}
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 flex justify-between items-center text-sm">
            <span className="text-gray-600">Applied Pricing Rule:</span>
            <span className="font-semibold text-gray-900">{getPricingRuleText()}</span>
          </div>

          {/* Footer Buttons */}
          <div className="flex justify-end gap-3 pt-4 border-t border-gray-100">
            <button type="button" onClick={onClose} className="px-5 py-2.5 text-sm font-medium border border-gray-200 rounded-lg text-gray-700 hover:bg-gray-50">
              Cancel
            </button>
            <button type="submit" disabled={loading} className="px-5 py-2.5 text-sm font-medium bg-[#008060] hover:bg-[#006e52] text-white rounded-lg disabled:opacity-50">
              {loading ? 'Importing...' : 'Import Product'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}