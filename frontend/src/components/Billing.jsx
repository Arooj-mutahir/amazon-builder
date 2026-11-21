// src/components/Billing.jsx
import { useState, useEffect } from "react";
import axios from "axios";
import { usePlan } from "../hooks/usePlan";
import { Sparkles, CheckCircle2, Loader2, TrendingDown } from "lucide-react";

export default function Billing() {
  const { isAdvance, refresh } = usePlan();
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const API_URL = import.meta.env.VITE_API_URL || `${window.location.origin}/api/shopify`;

  // 🔥 FIX: Payment ke baad redirect hone par UI update karo
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("success") === "true") {
      setSuccessMsg("🎉 Payment successful! You are now on the Advance Plan.");
      refresh(); 
      // URL clean karo
      const newUrl = window.location.pathname + window.location.search.replace(/[?&]success=true/, "").replace(/^&/, "?");
      window.history.replaceState({}, "", newUrl);
    } else if (params.get("error")) {
      setErrorMsg("Payment failed or cancelled. Please try again.");
      const newUrl = window.location.pathname + window.location.search.replace(/[?&]error=[^&]*/, "").replace(/^&/, "?");
      window.history.replaceState({}, "", newUrl);
    }
  }, [refresh]);

  const getShopDomain = () => {
    const params = new URLSearchParams(window.location.search);
    let shop = params.get("shop");
    if (!shop) {
      const pathMatch = window.location.pathname.match(/\/store\/([^\/]+)/);
      if (pathMatch && pathMatch[1]) shop = `${pathMatch[1]}.myshopify.com`;
    }
    return shop || "";
  };

  const handleUpgrade = async () => {
    const shop = getShopDomain();
    if (!shop) return setErrorMsg("Shop domain not found.");

    setLoading(true);
    setErrorMsg("");
    setSuccessMsg("");
    try {
      const res = await axios.post(`${API_URL}/billing/upgrade?shop=${shop}`);
      if (res.data?.confirmation_url) {
        window.open(res.data.confirmation_url, "_top");
      } else {
        setErrorMsg("No payment URL returned from Shopify.");
      }
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || "Upgrade failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleDowngrade = async () => {
    const shop = getShopDomain();
    if (!shop || !window.confirm("Are you sure you want to downgrade to Basic? You will lose Advance features.")) return;

    setLoading(true);
    setErrorMsg("");
    setSuccessMsg("");
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

      {/* 🔥 FIX: Success/Error Messages */}
      {successMsg && (
        <div className="mb-4 p-3 bg-green-50 text-green-700 text-sm rounded-lg border border-green-200 text-left font-medium">
          {successMsg}
        </div>
      )}

      {errorMsg && (
        <div className="mb-4 p-3 bg-red-50 text-red-600 text-sm rounded-lg border border-red-100 text-left">
          ❌ {errorMsg}
        </div>
      )}

      {/* 🔥 FIX: Ab dono messages ek saath nahi dikhenge */}
      {successMsg ? (
        // Agar abhi-abhi upgrade hua hai, toh sirf Downgrade button dikhao
        <button 
          onClick={handleDowngrade} 
          disabled={loading}
          className="w-full bg-red-50 text-red-600 border border-red-200 py-3 rounded-lg font-bold hover:bg-red-100 transition disabled:opacity-50 flex justify-center items-center gap-2"
        >
          {loading ? <Loader2 className="animate-spin" size={18} /> : <TrendingDown size={18} />}
          {loading ? "Processing..." : "Downgrade to Basic"}
        </button>
      ) : isAdvance ? (
        // Agar pehle se Advance hai, toh message + Downgrade dikhao
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
        // Agar Basic hai, toh Upgrade dikhao
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