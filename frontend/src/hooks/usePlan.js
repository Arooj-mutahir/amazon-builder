// src/hooks/usePlan.js
import { useEffect, useState } from "react";
import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || `${window.location.origin}/api/shopify`;

const FALLBACK = {
  plan: "basic",
  status: "active",
  features: {
    manual_sync: false, auto_sync: false, extra_pricing: false,
  },
};

export function usePlan() {
  const [data, setData] = useState(FALLBACK);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    try {
      const res = await axios.get(`${API_URL}/billing/status`);
      setData(res.data);
    } catch (err) {
      console.error("Plan fetch failed", err);
      setData(FALLBACK);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  return {
    ...data,
    loading,
    isAdvance: data.plan === "advance" && data.status === "active",
    isBasic: data.plan === "basic",
    refresh,
  };
}