import { CheckCircle2, XCircle } from 'lucide-react';

export default function Alerts({ error, successMsg }) {
  if (!error && !successMsg) return null;

  return (
    <div className="mt-4">
      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg flex items-center gap-2 mb-2 border border-red-100">
          <XCircle className="w-5 h-5 flex-shrink-0" /> {error}
        </div>
      )}
      {successMsg && (
        <div className="p-4 bg-green-50 text-green-700 rounded-lg flex items-center gap-2 mb-2 border border-green-100">
          <CheckCircle2 className="w-5 h-5 flex-shrink-0" /> {successMsg}
        </div>
      )}
    </div>
  );
}