// src/components/Billing.jsx
import { useState, useEffect } from "react";
import axios from "axios";
import { usePlan } from "../hooks/usePlan";
import { Sparkles, CheckCircle2, Loader2, TrendingDown, Clock, ShieldAlert } from "lucide-react";

export default function Billing() {
  const { isAdvance, isExpired, daysLeftInTrial, productCount, productLimit, refresh } = usePlan();
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const API_URL = import.meta.env.VITE_API_URL || `${window.location.origin}/api/shopify`;

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("success") === "true") {
      setSuccessMsg("🎉 Payment successful! Your plan has been updated.");
      refresh(); 
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

  const handleUpgrade = async (planType) => {
    const shop = getShopDomain();
    if (!shop) return setErrorMsg("Shop domain not found.");

    setLoading(true);
    setErrorMsg("");
    setSuccessMsg("");
    try {
      // 🔥 Plan type pass karo (basic ya advance)
      const res = await axios.post(`${API_URL}/billing/upgrade?shop=${shop}&plan=${planType}`);
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
    <div className="max-w-4xl mx-auto p-4 mt-6">
      
      {/* Trial Warning Banner */}
      {daysLeftInTrial > 0 && !isAdvance && !isExpired && (
        <div className="mb-6 bg-yellow-50 text-yellow-800 p-4 rounded-xl border border-yellow-200 flex items-center gap-3">
          <Clock className="text-yellow-600" size={24} />
          <div>
            <p className="font-bold">Your Basic Trial expires in {daysLeftInTrial} days.</p>
            <p className="text-sm">Subscribe to a plan below to keep your products and features.</p>
          </div>
        </div>
      )}

      {/* Expired Warning Banner */}
      {isExpired && (
        <div className="mb-6 bg-red-50 text-red-800 p-4 rounded-xl border border-red-200 flex items-center gap-3">
          <ShieldAlert className="text-red-600" size={24} />
          <div>
            <p className="font-bold">Your trial has expired!</p>
            <p className="text-sm">Please subscribe to a plan to continue importing and syncing products.</p>
          </div>
        </div>
      )}

      {/* Success/Error Messages */}
      {successMsg && (
        <div className="mb-6 p-4 bg-green-50 text-green-700 font-medium rounded-xl border border-green-200">
          {successMsg}
        </div>
      )}
      {errorMsg && (
        <div className="mb-6 p-4 bg-red-50 text-red-600 rounded-xl border border-red-200">
          ❌ {errorMsg}
        </div>
      )}

      {/* Product Usage (Agar active plan hai) */}
      <div className="mb-8 bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
        <h3 className="font-bold text-gray-800 mb-2">Current Usage</h3>
        <div className="flex justify-between text-sm mb-1 text-gray-600">
          <span>Products Imported</span>
          <span className="font-semibold">{productCount} / {productLimit}</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2.5">
          <div 
            className={`h-2.5 rounded-full ${productCount > productLimit * 0.9 ? 'bg-red-500' : 'bg-green-500'}`} 
            style={{ width: `${Math.min(100, (productCount / productLimit) * 100)}%` }}
          ></div>
        </div>
      </div>

      {/* Plans Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Basic Plan Card */}
        <div className={`bg-white border-2 rounded-xl p-6 relative ${!isAdvance && !isExpired ? 'border-blue-500' : 'border-gray-200'}`}>
          {!isAdvance && !isExpired && <div className="absolute top-0 right-0 bg-blue-500 text-white text-xs px-3 py-1 rounded-bl-lg font-bold">CURRENT PLAN</div>}
          <h2 className="text-xl font-bold mb-2">Basic Plan</h2>
          <p className="text-3xl font-extrabold mb-4">$5<span className="text-sm text-gray-500 font-normal">/mo</span></p>
          <p className="text-sm text-gray-500 mb-6">Perfect for small stores getting started with dropshipping.</p>
          
          <ul className="space-y-3 mb-8 text-sm text-gray-700">
            <li className="flex items-center gap-2"><CheckCircle2 size={18} className="text-green-500" /> <b>1,000</b> Product Variants</li>
            <li className="flex items-center gap-2"><CheckCircle2 size={18} className="text-green-500" /> Basic Pricing Rules</li>
            <li className="flex items-center gap-2"><CheckCircle2 size={18} className="text-green-500" /> Manual Product Import</li>
          </ul>

          {!isAdvance ? (
            <button 
              onClick={() => handleUpgrade("basic")} 
              disabled={loading}
              className="w-full py-3 bg-gray-900 text-white rounded-lg font-bold hover:bg-gray-800 transition disabled:opacity-50"
            >
              {loading ? "Processing..." : isExpired ? "Subscribe to Basic ($5/mo)" : "Switch to Basic ($5/mo)"}
            </button>
          ) : (
            <button 
              onClick={handleDowngrade} 
              disabled={loading}
              className="w-full py-3 bg-red-50 text-red-600 border border-red-200 rounded-lg font-bold hover:bg-red-100 transition disabled:opacity-50 flex justify-center items-center gap-2"
            >
              {loading ? <Loader2 className="animate-spin" size={18} /> : <TrendingDown size={18} />}
              {loading ? "Processing..." : "Downgrade to Basic"}
            </button>
          )}
        </div>

        {/* Advance Plan Card */}
        <div className={`bg-white border-2 rounded-xl p-6 relative ${isAdvance ? 'border-purple-500' : 'border-gray-200'}`}>
          {isAdvance && <div className="absolute top-0 right-0 bg-purple-500 text-white text-xs px-3 py-1 rounded-bl-lg font-bold">CURRENT PLAN</div>}
          {!isAdvance && <div className="absolute top-0 right-0 bg-gradient-to-r from-purple-600 to-pink-600 text-white text-xs px-3 py-1 rounded-bl-lg font-bold">RECOMMENDED</div>}
          
          <h2 className="text-xl font-bold mb-2">Advance Plan</h2>
          <p className="text-3xl font-extrabold mb-4">$19.99<span className="text-sm text-gray-500 font-normal">/mo</span></p>
          <p className="text-sm text-gray-500 mb-6">For serious sellers who want automation and advanced features.</p>
          
          <ul className="space-y-3 mb-8 text-sm text-gray-700">
            <li className="flex items-center gap-2"><CheckCircle2 size={18} className="text-green-500" /> <b>10,000</b> Product Variants</li>
            <li className="flex items-center gap-2"><CheckCircle2 size={18} className="text-green-500" /> Automatic Nightly Price/Stock Sync</li>
            <li className="flex items-center gap-2"><CheckCircle2 size={18} className="text-green-500" /> Compare At Price Settings</li>
            <li className="flex items-center gap-2"><CheckCircle2 size={18} className="text-green-500" /> Size Chart & Metafields</li>
            <li className="flex items-center gap-2"><CheckCircle2 size={18} className="text-green-500" /> Add up to 5 Team Members</li>
          </ul>

          {!isAdvance ? (
            <button 
              onClick={() => handleUpgrade("advance")} 
              disabled={loading}
              className="w-full py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg font-bold hover:opacity-90 transition disabled:opacity-50 flex justify-center items-center gap-2"
            >
              {loading ? <Loader2 className="animate-spin" size={18} /> : <Sparkles size={18} />}
              {loading ? "Redirecting..." : "Upgrade to Advance ($19.99/mo)"}
            </button>
          ) : (
            <button 
              disabled
              className="w-full py-3 bg-gray-100 text-gray-500 rounded-lg font-bold cursor-not-allowed"
            >
              Already on Advance Plan
            </button>
          )}
        </div>

      </div>
    </div>
  );
}