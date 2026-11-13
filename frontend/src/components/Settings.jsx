import { useState } from 'react';
import axios from 'axios'; 
import { Save, ArrowLeft, Percent, DollarSign, Receipt, Sparkles } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || `${window.location.origin}/api/shopify`;

export default function Settings({ onBack, shopDomain }) {
  const [markup, setMarkup] = useState(localStorage.getItem('global_markup') || '0');
  const [markupType, setMarkupType] = useState(localStorage.getItem('global_markup_type') || 'percent');
  const [extraPercent, setExtraPercent] = useState(localStorage.getItem('global_extra_percent') || '0');
  const [taxRate, setTaxRate] = useState(localStorage.getItem('global_tax_rate') || '0');
  const [saved, setSaved] = useState(false);

  const handleSave = async () => {
    // ✅ FIX: Agar 'both' select nahi hai, toh extra percent forcefully 0 karo
    const finalExtraPercent = markupType === 'both' ? parseFloat(extraPercent || 0) : 0;

    // 1. LocalStorage update karo (UI ke liye)
    localStorage.setItem('global_markup', markup);
    localStorage.setItem('global_markup_type', markupType);
    localStorage.setItem('global_extra_percent', finalExtraPercent.toString()); // ✅ 0 save hoga
    localStorage.setItem('global_tax_rate', taxRate);

    // 2. Database update karo (Cron Job ke liye)
    try {
      await axios.post(`${API_URL}/app/save-settings`, {
        shop_domain: shopDomain,
        markup: parseFloat(markup || 0),
        markup_type: markupType,
        extra_percent: finalExtraPercent, // ✅ Yahan 0 jayega
        tax_rate: parseFloat(taxRate || 0)
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (error) {
      console.error("Failed to save to DB", error);
      alert("Settings could not be saved to database. Check backend terminal.");
    }
  };

  return (
    <div className="bg-white/90 dark:bg-gray-900/90 backdrop-blur-md rounded-3xl shadow-xl shadow-gray-200/50 dark:shadow-none border border-white dark:border-gray-800 p-8 transition-colors duration-300">
      <div className="flex items-center gap-4 mb-8 border-b border-gray-100 dark:border-gray-800 pb-6">
        <button 
          onClick={onBack} 
          className="p-2.5 bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 rounded-xl transition text-gray-600 dark:text-gray-300"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h2 className="text-2xl font-extrabold text-gray-900 dark:text-white flex items-center gap-2">
            Pricing Settings <Sparkles className="w-5 h-5 text-yellow-500" />
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Configure global pricing rules for all products.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-3xl">
        
        {/* Markup Type Dropdown */}
        <div className="md:col-span-2">
          <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2.5">Markup Strategy</label>
          <select
            className="w-full px-5 py-3.5 bg-blue-50/50 dark:bg-gray-800 border border-blue-100 dark:border-gray-700 rounded-xl text-gray-900 dark:text-white font-semibold focus:bg-white dark:focus:bg-gray-800 focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 outline-none transition-all cursor-pointer"
            value={markupType}
            onChange={(e) => {
              setMarkupType(e.target.value);
              // ✅ FIX: Agar user 'both' se kisi aur par switch kare, toh Extra 0 ho jaye
              if (e.target.value !== 'both') {
                setExtraPercent('0');
                localStorage.setItem('global_extra_percent', '0');
              }
            }}
          >
            <option value="percent">Percentage Only (%)</option>
            <option value="fixed">Fixed Amount Only ($)</option>
            <option value="both">Fixed + Percentage</option>
          </select>
        </div>

        {/* Markup Value */}
        <div>
          <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2.5 flex items-center gap-2">
            {markupType === 'percent' ? <Percent className="w-4 h-4 text-blue-500" /> : <DollarSign className="w-4 h-4 text-green-500" />}
            {markupType === 'percent' ? 'Markup Percentage (%)' : 'Fixed Amount ($)'}
          </label>
          <input
            type="number"
            className="w-full px-5 py-3.5 bg-gray-50/50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-gray-900 dark:text-white font-medium focus:bg-white dark:focus:bg-gray-800 focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 outline-none transition-all"
            value={markup}
            onChange={(e) => setMarkup(e.target.value)}
          />
        </div>

        {/* Extra Percent (Sirf tab dikhega jab 'both' select ho) */}
        {markupType === 'both' ? (
          <div>
            <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2.5 flex items-center gap-2">
              <Percent className="w-4 h-4 text-purple-500" /> Extra Percentage (%)
            </label>
            <input
              type="number"
              className="w-full px-5 py-3.5 bg-purple-50/30 dark:bg-gray-800 border border-purple-100 dark:border-gray-700 rounded-xl text-gray-900 dark:text-white font-medium focus:bg-white dark:focus:bg-gray-800 focus:ring-2 focus:ring-purple-500/30 focus:border-purple-500 outline-none transition-all"
              value={extraPercent}
              onChange={(e) => setExtraPercent(e.target.value)}
            />
          </div>
        ) : <div></div>}

        {/* Tax Rate Input */}
        <div className="md:col-span-2">
          <label className="block text-sm font-bold text-gray-700 dark:text-gray-300 mb-2.5 flex items-center gap-2">
            <Receipt className="w-4 h-4 text-orange-500" /> Tax Rate (%)
          </label>
          <input
            type="number"
            className="w-full px-5 py-3.5 bg-orange-50/30 dark:bg-gray-800 border border-orange-100 dark:border-gray-700 rounded-xl text-gray-900 dark:text-white font-medium focus:bg-white dark:focus:bg-gray-800 focus:ring-2 focus:ring-orange-500/30 focus:border-orange-500 outline-none transition-all"
            value={taxRate}
            onChange={(e) => setTaxRate(e.target.value)}
          />
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-2 font-medium">This tax will be added on top of the final calculated price.</p>
        </div>
      </div>

      <div className="mt-10 pt-6 border-t border-gray-100 dark:border-gray-800 flex items-center gap-4">
        <button
          onClick={handleSave}
          className="bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white px-8 py-3.5 rounded-2xl font-bold shadow-lg shadow-green-500/30 dark:shadow-none flex items-center gap-2 transition-all transform hover:-translate-y-0.5"
        >
          <Save className="w-5 h-5" /> Save Configuration
        </button>
        {saved && <span className="text-sm font-bold text-emerald-600 dark:text-emerald-400 animate-pulse">✅ Settings saved successfully!</span>}
      </div>
    </div>
  );
}