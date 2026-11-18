// src/components/PricingSummary.jsx
import { BadgePercent, Sparkles } from 'lucide-react';

export default function PricingSummary({ markup, markupType, extraPercent, taxRate }) {
  return (
    <div className="bg-white rounded-xl p-4 md:p-5 border border-gray-200 shadow-sm relative overflow-hidden w-full h-full">
      {/* Background Icon - subtle */}
      <div className="absolute -right-4 -top-4 opacity-[0.03]">
        <Sparkles className="w-24 h-24 text-gray-900" />
      </div>
      
      <label className="flex items-center gap-2 text-sm font-bold text-gray-800 mb-4">
        <BadgePercent className="w-4 h-4 text-blue-600" /> Active Pricing
      </label>
      
      <div className="space-y-2 text-xs md:text-sm">
        <div className="flex justify-between items-center bg-gray-50 px-3 py-2 rounded-lg border border-gray-100">
          <span className="text-gray-600">Strategy</span> 
          <span className="font-bold text-gray-900 capitalize">{markupType}</span>
        </div>
        <div className="flex justify-between items-center bg-gray-50 px-3 py-2 rounded-lg border border-gray-100">
          <span className="text-gray-600">Markup</span> 
          <span className="font-bold text-gray-900">{markup} {markupType === 'percent' ? '%' : '$'}</span>
        </div>
        {markupType === 'both' && (
          <div className="flex justify-between items-center bg-gray-50 px-3 py-2 rounded-lg border border-gray-100">
            <span className="text-gray-600">Extra %</span> 
            <span className="font-bold text-gray-900">{extraPercent}%</span>
          </div>
        )}
        <div className="flex justify-between items-center bg-gray-50 px-3 py-2 rounded-lg border border-gray-100">
          <span className="text-gray-600">Tax Rate</span> 
          <span className="font-bold text-orange-600">{taxRate}%</span>
        </div>
      </div>
    </div>
  );
}