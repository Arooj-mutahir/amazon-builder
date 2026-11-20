import { useState } from "react";
import axios from "axios";
import { usePlan } from "../hooks/usePlan";

export default function Billing() {
  const { plan, refresh } = usePlan();
  const [loading, setLoading] = useState(false);

  const handleUpgrade = async () => {
    setLoading(true);
    try {
      await axios.post("http://localhost:8000/api/shopify/billing/upgrade");
      await refresh(); // State update karo taaki UI turant badle
      alert("Successfully upgraded to Advance Plan! 🎉");
    } catch (err) {
      alert("Upgrade failed. Check console.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto p-8 mt-10 bg-white border rounded-xl shadow-lg text-center">
      <h1 className="text-2xl font-bold mb-2">Go Unlimited</h1>
      <p className="text-gray-500 mb-6">Unlock Auto-Sync, Team Members, and Advanced Pricing.</p>
      
      <ul className="text-left space-y-3 mb-8 text-sm text-gray-700">
        <li>✅ Automatic Nightly Price/Stock Sync</li>
        <li>✅ Add up to 5 Team Members</li>
        <li>✅ Compare At Price Settings</li>
        <li>✅ Size Chart & Metafields</li>
      </ul>

      {plan === "advance" ? (
        <div className="bg-green-100 text-green-700 p-3 rounded-lg font-medium">
          You are already on the Advance Plan!
        </div>
      ) : (
        <button 
          onClick={handleUpgrade} 
          disabled={loading}
          className="w-full bg-gradient-to-r from-purple-600 to-pink-600 text-white py-3 rounded-lg font-bold hover:opacity-90 disabled:opacity-50"
        >
          {loading ? "Upgrading..." : "Upgrade Now"}
        </button>
      )}
    </div>
  );
}