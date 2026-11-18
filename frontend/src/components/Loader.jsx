// src/components/Loader.jsx
import { Loader2 } from 'lucide-react';

export default function Loader({ message = "Loading..." }) {
  return (
    <div className="flex flex-col items-center justify-center p-20 min-h-[400px] w-full">
      <Loader2 className="w-10 h-10 animate-spin text-[#008060] mb-4" />
      <p className="text-sm text-gray-500 font-medium">{message}</p>
    </div>
  );
}