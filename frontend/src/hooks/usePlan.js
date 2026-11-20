// src/hooks/usePlan.js
import { useEffect, useState, useCallback } from "react";
import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || `${window.location.origin}/api/shopify`;

const FALLBACK = {
  plan: "basic",
  status: "active",
  features: {
    manual_sync: false, 
    auto_sync: false, 
    extra_pricing: false,
  },
};

export function usePlan() {
  const [data, setData] = useState(FALLBACK);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async (showLoader = false) => {
    // 🔥 FIX: Default mein loader nahi dikhayenge. 
    // App.jsx initial load pe 'loading' check karega. 
    // Billing page pe upgrade ke baad loader nahi aayega, UI smoothly update hoga.
    if (showLoader) setLoading(true);

    try {
      // 1. Shopify URL se shop domain nikalo
      const urlParams = new URLSearchParams(window.location.search);
      const shop = urlParams.get('shop');

      if (!shop) {
        console.warn("Shop domain not found in URL, using fallback basic plan.");
        setData(FALLBACK);
        return;
      }

      // 2. Backend se store details fetch karo
      const res = await axios.get(`${API_URL}/stores/by-shop?shop=${shop}`);
      const storeData = res.data || {};
      
      // 3. Sahi format mein data set karo
      setData({
        plan: (storeData.plan || "basic").toLowerCase(), 
        status: (storeData.plan_status || "active").toLowerCase(), 
        features: {
          manual_sync: (storeData.plan || "").toLowerCase() === "advance",
          auto_sync: (storeData.plan || "").toLowerCase() === "advance",
          extra_pricing: (storeData.plan || "").toLowerCase() === "advance",
        }
      });

    } catch (err) {
      console.error("Plan fetch failed:", err);
      // 🔥 FIX: Agar network error aaye, toh purana data hi rakho, 
      // forcefully basic mat banao (warna upgrade ke baad error aane pe downgrade ho jayega)
    } finally {
      if (showLoader) setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Initial load pe loader dikhao
    refresh(true);
  }, [refresh]);

  return {
    ...data,
    loading,
    // 🔥 Strict Check: Sirf tabhi Advance maano jab plan 'advance' ho AUR status 'active' ho
    isAdvance: data.plan === "advance" && data.status === "active",
    isBasic: data.plan === "basic" || !data.plan,
    refresh,
  };
}