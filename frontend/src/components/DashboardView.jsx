import ProductForm from './ProductForm';
import Alerts from './Alerts';

export default function DashboardView({ 
  url, setUrl, loading, onSubmit,
  selectedStore,
  collections, selectedCollections, setSelectedCollections,
  markup, markupType, extraPercent, taxRate,
  error, successMsg,
  onConnectStore
}) {
  return (
    <div className="bg-white/90 dark:bg-gray-900/90 backdrop-blur-sm rounded-3xl shadow-xl shadow-gray-200/50 dark:shadow-none border border-white dark:border-gray-800 p-4 md:p-8 transition-all duration-300 w-full">

      {/* ✅ Show active store badge (auto-detected, no manual dropdown) */}
      {selectedStore && (
        <div className="mb-4 inline-flex items-center gap-2 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-400 text-xs font-semibold px-3 py-1.5 rounded-full">
          <span className="w-2 h-2 bg-green-500 rounded-full inline-block"></span>
          Connected: {selectedStore}
        </div>
      )}

      <ProductForm 
        url={url} setUrl={setUrl}
        loading={loading} onSubmit={onSubmit}
        collections={collections}
        selectedCollections={selectedCollections}
        setSelectedCollections={setSelectedCollections}
        markup={markup} markupType={markupType}
        extraPercent={extraPercent} taxRate={taxRate}
      />
      <Alerts error={error} successMsg={successMsg} />
    </div>
  );
}
