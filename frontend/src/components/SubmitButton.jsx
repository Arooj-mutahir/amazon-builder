import { UploadCloud, Loader2 } from 'lucide-react';

export default function SubmitButton({ onSubmit, loading }) {
  return (
    <div className="flex justify-end pt-4 border-t border-gray-100 dark:border-gray-800 w-full">
      <button
        onClick={onSubmit}
        disabled={loading}
        className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white px-6 md:px-8 py-3 md:py-3.5 rounded-2xl font-bold shadow-lg shadow-blue-500/30 dark:shadow-none flex items-center justify-center gap-2 transition-all disabled:opacity-50 w-full md:w-auto transform hover:-translate-y-0.5 text-sm md:text-base"
      >
        {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <UploadCloud className="w-5 h-5" />}
        {loading ? 'Pushing...' : 'Fetch & Push to Shopify'}
      </button>
    </div>
  );
}