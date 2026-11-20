// src/components/Settings.jsx
import { useState } from 'react';
import axios from 'axios'; 
import { Save, ArrowLeft, Percent, DollarSign, Receipt, Sparkles, TrendingUp, Lock } from 'lucide-react';
import { usePlan } from '../hooks/usePlan'; // 👈 Naya Hook Import

const API_URL = import.meta.env.VITE_API_URL || `${window.location.origin}/api/shopify`;

export default function Settings({ onBack, storeId }) {
  const { isAdvance } = usePlan(); // 👈 Plan check
  
  const [markup, setMarkup] = useState(localStorage.getItem('global_markup') || '0');
  const [markupType, setMarkupType] = useState(localStorage.getItem('global_markup_type') || 'percent');
  const [extraPercent, setExtraPercent] = useState(localStorage.getItem('global_extra_percent') || '0');
  const [taxRate, setTaxRate] = useState(localStorage.getItem('global_tax_rate') || '0');
  const [comparePriceMarkup, setComparePriceMarkup] = useState(localStorage.getItem('global_compare_markup') || '0');
  const [saved, setSaved] = useState(false);

  const handleSave = async () => {
    if (!storeId) {
      alert("No store connected. Please reload the app.");
      return;
    }

    const finalExtraPercent = markupType === 'both' ? parseFloat(extraPercent || 0) : 0;

    // Save to LocalStorage
    localStorage.setItem('global_markup', markup);
    localStorage.setItem('global_markup_type', markupType);
    localStorage.setItem('global_extra_percent', finalExtraPercent.toString());
    localStorage.setItem('global_tax_rate', taxRate);
    localStorage.setItem('global_compare_markup', comparePriceMarkup);

    try {
      await axios.post(`${API_URL}/app/save-settings`, {
        store_id: storeId,
        markup: parseFloat(markup || 0),
        markup_type: markupType,
        extra_percent: finalExtraPercent,
        tax_rate: parseFloat(taxRate || 0),
        compare_price_markup: parseFloat(comparePriceMarkup || 0),
        default_stock_qty: 100, 
        shopify_location_id: null
      });
      
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (error) {
      console.error("Failed to save to DB", error);
      alert("Settings could not be saved to database. Check backend terminal.");
    }
  };

  return (
    <div className="bg-white rounded-3xl shadow-sm border border-gray-200 p-8">
      
      {/* Header */}
      <div className="flex items-center gap-4 mb-8 border-b border-gray-100 pb-6">
        <button 
          onClick={onBack} 
          className="p-2.5 bg-gray-50 hover:bg-gray-100 rounded-xl transition text-gray-600"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h2 className="text-2xl font-extrabold text-gray-900 flex items-center gap-2">
            Pricing Settings <Sparkles className="w-5 h-5 text-yellow-500" />
          </h2>
          <p className="text-sm text-gray-500 mt-1">Configure global pricing rules for all products.</p>
        </div>
      </div>

      {/* ✅ Grid Layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl relative">
        
        {/* 1. Markup Strategy (BASIC) */}
        <div>
          <label className="block text-sm font-bold text-gray-700 mb-2.5">Markup Strategy</label>
          <select
            className="w-full px-5 py-3.5 bg-blue-50/50 border border-blue-100 rounded-xl text-gray-900 font-semibold focus:bg-white focus:ring-2 focus:ring-blue-500/30 outline-none transition-all cursor-pointer"
            value={markupType}
            onChange={(e) => {
              setMarkupType(e.target.value);
              if (e.target.value !== 'both') {
                setExtraPercent('0');
                localStorage.setItem('global_extra_percent', '0');
              }
            }}
          >
            <option value="percent">Percentage Only (%)</option>
            <option value="fixed">Fixed Amount Only ($)</option>
            {isAdvance && <option value="both">Fixed + Percentage (Advance)</option>}
          </select>
        </div>

        {/* 2. Markup Value (BASIC) */}
        <div>
          <label className="block text-sm font-bold text-gray-700 mb-2.5 flex items-center gap-2">
            {markupType === 'percent' ? <Percent className="w-4 h-4 text-blue-500" /> : <DollarSign className="w-4 h-4 text-green-500" />}
            {markupType === 'percent' ? 'Markup Percentage (%)' : 'Fixed Amount ($)'}
          </label>
          <input
            type="number"
            className="w-full px-5 py-3.5 bg-gray-50/50 border border-gray-200 rounded-xl text-gray-900 font-medium focus:bg-white focus:ring-2 focus:ring-blue-500/30 outline-none transition-all"
            value={markup}
            onChange={(e) => setMarkup(e.target.value)}
          />
        </div>

        {/* =========================================
            ADVANCE FIELDS SECTION (Locked for Basic)
           ========================================= */}
        <div className="md:col-span-2 relative">
          
          {/* Lock Overlay for Basic Users */}
          {!isAdvance && (
            <div className="absolute inset-0 bg-white/60 backdrop-blur-sm z-10 flex flex-col items-center justify-center rounded-2xl border border-dashed border-gray-300">
              <Lock className="text-gray-600 mb-2" size={28} />
              <p className="text-sm font-bold text-gray-800">Advance Plan Required</p>
              <p className="text-xs text-gray-500 mb-3">Unlock Tax, Extra %, and Compare Price logic.</p>
              <button 
                onClick={() => window.location.href = '/billing'} 
                className="bg-gradient-to-r from-purple-600 to-pink-600 text-white px-5 py-2 rounded-lg text-sm font-bold shadow-md hover:opacity-90"
              >
                Upgrade to Advance
              </button>
            </div>
          )}

          {/* Ye Fields Basic pe blur rahenge */}
          <div className={`grid grid-cols-1 md:grid-cols-2 gap-6 ${!isAdvance ? 'opacity-40 pointer-events-none' : ''}`}>
            
            {/* 3. Extra Percent (Only for Both) */}
            {markupType === 'both' && (
              <div>
                <label className="block text-sm font-bold text-gray-700 mb-2.5 flex items-center gap-2">
                  <Percent className="w-4 h-4 text-purple-500" /> Extra Percentage (%)
                </label>
                <input
                  type="number"
                  className="w-full px-5 py-3.5 bg-purple-50/30 border border-purple-100 rounded-xl text-gray-900 font-medium focus:bg-white focus:ring-2 focus:ring-purple-500/30 outline-none transition-all"
                  value={extraPercent}
                  onChange={(e) => setExtraPercent(e.target.value)}
                />
              </div>
            )}

            {/* 4. Tax Rate */}
            <div>
              <label className="block text-sm font-bold text-gray-700 mb-2.5 flex items-center gap-2">
                <Receipt className="w-4 h-4 text-orange-500" /> Tax Rate (%)
              </label>
              <input
                type="number"
                className="w-full px-5 py-3.5 bg-orange-50/30 border border-orange-100 rounded-xl text-gray-900 font-medium focus:bg-white focus:ring-2 focus:ring-orange-500/30 outline-none transition-all"
                value={taxRate}
                onChange={(e) => setTaxRate(e.target.value)}
              />
            </div>

            {/* 5. Compare at Price */}
            <div>
              <label className="block text-sm font-bold text-gray-700 mb-2.5 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-pink-500" /> Compare at Price Markup (%)
              </label>
              <input
                type="number"
                className="w-full px-5 py-3.5 bg-pink-50/30 border border-pink-100 rounded-xl text-gray-900 font-medium focus:bg-white focus:ring-2 focus:ring-pink-500/30 outline-none transition-all"
                value={comparePriceMarkup}
                onChange={(e) => setComparePriceMarkup(e.target.value)}
              />
            </div>

          </div>
        </div>
      </div>

      {/* Info Text */}
      <div className="mt-4 max-w-4xl text-xs text-gray-500 space-y-1">
        {markupType === 'both' && <p>* Extra percentage is applied after fixed amount markup.</p>}
        <p>* Tax Rate will be added on top of the final calculated price.</p>
        <p>* Compare at Price is calculated based on the final price (e.g., Final Price $100 + 20% = Compare Price $120).</p>
      </div>

      {/* Save Button */}
      <div className="mt-10 pt-6 border-t border-gray-100 flex items-center gap-4">
        <button
          onClick={handleSave}
          className="bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white px-8 py-3.5 rounded-2xl font-bold shadow-lg shadow-green-500/30 flex items-center gap-2 transition-all transform hover:-translate-y-0.5"
        >
          <Save className="w-5 h-5" /> Save Configuration
        </button>
        {saved && <span className="text-sm font-bold text-emerald-600 animate-pulse">✅ Settings saved successfully!</span>}
      </div>
    </div>
  );
}