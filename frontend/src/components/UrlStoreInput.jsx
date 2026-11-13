import React from 'react';
import UrlStoreInput from './UrlStoreInput';
import PricingSummary from './PricingSummary';
import CollectionSelector from './CollectionSelector';
import SubmitButton from './SubmitButton';

export default function ProductForm({ 
  url, setUrl, loading, onSubmit, 
  collections, selectedCollections, setSelectedCollections,
  markup, markupType, extraPercent, taxRate
}) {
  const handleCollectionToggle = (id) => {
    if (selectedCollections.includes(id)) {
      setSelectedCollections(selectedCollections.filter(cId => cId !== id));
    } else {
      setSelectedCollections([...selectedCollections, id]);
    }
  };

  return (
    <div className="space-y-6 md:space-y-8 w-full">
      <UrlStoreInput url={url} setUrl={setUrl} loading={loading} />

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 md:gap-6 w-full">
        <PricingSummary markup={markup} markupType={markupType} extraPercent={extraPercent} taxRate={taxRate} />
        <CollectionSelector collections={collections} selectedCollections={selectedCollections} onToggle={handleCollectionToggle} loading={loading} />
      </div>

      <SubmitButton onSubmit={onSubmit} loading={loading} />
    </div>
  );
}