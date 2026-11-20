// src/components/Billing.jsx
import { useState } from "react";
import axios from "axios";
import { usePlan } from "../hooks/usePlan";
import { Sparkles, CheckCircle2, Loader2, TrendingDown } from "lucide-react";

export default function Billing() {
  const { isAdvance, refresh } = usePlan();
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const API_URL = import.meta.env.VITE_API_URL || `${window.location.origin}/api/shopify`;

  // 🔥 URL se shop domain nikalo
  const getShopDomain = () => {
    const params = new URLSearchParams(window.location.search);
    return params.get("shop") || "";
  };

  const handleUpgrade = async () => {
    const shop = getShopDomain();
    if (!shop) {
      setErrorMsg("Shop domain not found in URL. Please reload from Shopify admin.");
      return;
    }

    setLoading(true);
    setErrorMsg("");
    try {
      // 🔥 Shopify payment page URL request karo
      const res = await axios.post(`${API_URL}/billing/upgrade?shop=${shop}`);
      
      if (res.data?.confirmation_url) {
        // 🔥 Payment page pe redirect (Shopify App Bridge force karta hai "_top")
        window.open(res.data.confirmation_url, "_top");
      } else {
        setErrorMsg("No payment URL returned from Shopify.");
      }
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || "Upgrade failed. Check backend.");
    } finally {
      setLoading(false);
    }
  };

  const handleDowngrade = async () => {
    const shop = getShopDomain();
    if (!shop) return;

    if (!window.confirm("Are you sure you want to downgrade to Basic?")) return;

    setLoading(true);
    setErrorMsg("");
    try {
      await axios.post(`${API_URL}/billing/downgrade?shop=${shop}`);
      await refresh();
      alert("Downgraded to Basic Plan.");
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || "Downgrade failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto p-8 mt-10 bg-white border border-gray-200 rounded-xl shadow-lg text-center">
      <h1 className="text-2xl font-bold mb-2 flex justify-center items-center gap-2">
        Go Unlimited <Sparkles className="text-yellow-500" size={24} />
      </h1>
      <p className="text-gray-500 mb-6">Unlock Auto-Sync, Team Members, and Advanced Pricing.</p>
      
      <ul className="text-left space-y-3 mb-8 text-sm text-gray-700">
        <li className="flex items-center gap-2"><CheckCircle2 size={18} className="text-green-500" /> Automatic Nightly Price/Stock Sync</li>
        <li className="flex items-center gap-2"><CheckCircle2 size={18} className="text-green-500" /> Add up to 5 Team Members</li>
        <li className="flex items-center gap-2"><CheckCircle2 size={18} className="text-green-500" /> Compare At Price Settings</li>
        <li className="flex items-center gap-2"><CheckCircle2 size={18} className="text-green-500" /> Size Chart & Metafields</li>
      </ul>

      {errorMsg && (
        <div className="mb-4 p-3 bg-red-50 text-red-600 text-sm rounded-lg border border-red-100 text-left">
          ❌ {errorMsg}
        </div>
      )}

      {isAdvance ? (
        <div className="space-y-4">
          <div className="bg-green-100 text-green-700 p-3 rounded-lg font-medium">
            ✅ You are already on the Advance Plan!
          </div>
          <button 
            onClick={handleDowngrade} 
            disabled={loading}
            className="w-full bg-red-50 text-red-600 border border-red-200 py-3 rounded-lg font-bold hover:bg-red-100 transition disabled:opacity-50 flex justify-center items-center gap-2"
          >
            {loading ? <Loader2 className="animate-spin" size={18} /> : <TrendingDown size={18} />}
            {loading ? "Processing..." : "Downgrade to Basic"}
          </button>
        </div>
      ) : (
        <button 
          onClick={handleUpgrade} 
          disabled={loading}
          className="w-full bg-gradient-to-r from-purple-600 to-pink-600 text-white py-3 rounded-lg font-bold hover:opacity-90 transition disabled:opacity-50 flex justify-center items-center gap-2"
        >
          {loading ? <Loader2 className="animate-spin" size={18} /> : <Sparkles size={18} />}
          {loading ? "Redirecting to Shopify..." : "Upgrade Now ($19.99/mo)"}
        </button>
      )}
    </div>
  );
}