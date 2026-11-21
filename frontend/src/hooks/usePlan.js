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
  // 🔥 NAYA: Trial & Limit fallbacks
  daysLeftInTrial: 0,
  productCount: 0,
  productLimit: 1000,
};

export function usePlan() {
  const [data, setData] = useState(FALLBACK);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async (showLoader = false) => {
    if (showLoader) setLoading(true);

    try {
      const urlParams = new URLSearchParams(window.location.search);
      const shop = urlParams.get('shop');

      if (!shop) {
        console.warn("Shop domain not found in URL, using fallback basic plan.");
        setData(FALLBACK);
        return;
      }

      const res = await axios.get(`${API_URL}/stores/by-shop?shop=${shop}`);
      const storeData = res.data || {};
      
      setData({
        plan: (storeData.plan || "basic").toLowerCase(), 
        status: (storeData.plan_status || "active").toLowerCase(), 
        features: {
          manual_sync: (storeData.plan || "").toLowerCase() === "advance",
          auto_sync: (storeData.plan || "").toLowerCase() === "advance",
          extra_pricing: (storeData.plan || "").toLowerCase() === "advance",
        },
        // 🔥 NAYA: Trial aur Limit data backend se set karo
        daysLeftInTrial: storeData.days_left_in_trial || 0,
        productCount: storeData.product_count || 0,
        productLimit: storeData.product_limit || 1000,
      });

    } catch (err) {
      console.error("Plan fetch failed:", err);
    } finally {
      if (showLoader) setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh(true);
  }, [refresh]);

  return {
    ...data,
    loading,
    isAdvance: data.plan === "advance" && data.status === "active",
    isBasic: data.plan === "basic" || !data.plan,
    isExpired: data.status === "expired", // 🔥 NAYA
    refresh,
  };
}