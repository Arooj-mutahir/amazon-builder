import { BadgePercent, Sparkles } from 'lucide-react';

export default function PricingSummary({ markup, markupType, extraPercent, taxRate }) {
  return (
    <div className="lg:col-span-2 bg-gradient-to-br from-indigo-50 to-blue-50 dark:from-gray-800 dark:to-gray-800 rounded-2xl p-4 md:p-5 border border-blue-100 dark:border-gray-700 shadow-sm relative overflow-hidden w-full">
      <div className="absolute -right-4 -top-4 opacity-10">
        <Sparkles className="w-24 h-24 text-blue-600" />
      </div>
      <label className="flex items-center gap-2 text-sm font-bold text-indigo-900 dark:text-blue-300 mb-4">
        <BadgePercent className="w-4 h-4" /> Active Pricing
      </label>
      
      <div className="space-y-2 text-xs md:text-sm">
        <div className="flex justify-between items-center bg-white/60 dark:bg-gray-900/50 px-3 py-2 rounded-lg">
          <span className="text-gray-600 dark:text-gray-400">Strategy</span> 
          <span className="font-bold text-indigo-700 dark:text-white capitalize">{markupType}</span>
        </div>
        <div className="flex justify-between items-center bg-white/60 dark:bg-gray-900/50 px-3 py-2 rounded-lg">
          <span className="text-gray-600 dark:text-gray-400">Markup</span> 
          <span className="font-bold text-indigo-700 dark:text-white">{markup} {markupType === 'percent' ? '%' : '$'}</span>
        </div>
        {markupType === 'both' && (
          <div className="flex justify-between items-center bg-white/60 dark:bg-gray-900/50 px-3 py-2 rounded-lg">
            <span className="text-gray-600 dark:text-gray-400">Extra %</span> 
            <span className="font-bold text-indigo-700 dark:text-white">{extraPercent}%</span>
          </div>
        )}
        <div className="flex justify-between items-center bg-white/60 dark:bg-gray-900/50 px-3 py-2 rounded-lg">
          <span className="text-gray-600 dark:text-gray-400">Tax Rate</span> 
          <span className="font-bold text-orange-600 dark:text-orange-400">{taxRate}%</span>
        </div>
      </div>
    </div>
  );
}