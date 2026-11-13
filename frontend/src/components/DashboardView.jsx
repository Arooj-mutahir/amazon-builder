import ProductForm from './ProductForm';
import Alerts from './Alerts';

export default function DashboardView({ 
  url, setUrl, loading, onSubmit, 
  stores, selectedStore, setSelectedStore,
  collections, selectedCollections, setSelectedCollections,
  markup, markupType, extraPercent, taxRate,
  error, successMsg
}) {
  return (
    <div className="bg-white/90 dark:bg-gray-900/90 backdrop-blur-sm rounded-3xl shadow-xl shadow-gray-200/50 dark:shadow-none border border-white dark:border-gray-800 p-4 md:p-8 transition-all duration-300 w-full">
      <ProductForm 
        url={url} setUrl={setUrl}
        loading={loading} onSubmit={onSubmit}
        stores={stores} selectedStore={selectedStore} setSelectedStore={setSelectedStore}
        collections={collections} selectedCollections={selectedCollections} setSelectedCollections={setSelectedCollections}
        markup={markup} markupType={markupType} extraPercent={extraPercent} taxRate={taxRate}
      />
      <Alerts error={error} successMsg={successMsg} />
    </div>
  );
}