import { useState, useEffect, useCallback } from 'react';
import { supabase } from '../lib/supabase';

export function useTools() {
  const [tools, setTools] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchTools = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data, error: fetchError } = await supabase
        .from('ai_tools')
        .select('*')
        .order('created_at', { ascending: false });

      if (!fetchError && data && data.length > 0) {
        try {
          const localRes = await fetch('/api/pipeline/entities');
          if (localRes.ok) {
            const localEntities = await localRes.json();
            const localMap = new Map(localEntities.map((e) => [e.id, e]));
            const merged = data.map((item) => {
              const local = localMap.get(item.id);
              return {
                ...item,
                pricing: item.pricing || local?.pricing || '',
                features: item.features || local?.features || [],
              };
            });
            setTools(merged);
            return;
          }
        } catch {
          // Ignore local fetch error and use Supabase data
        }
        setTools(data);
      } else {
        // Fallback to local /api/pipeline/entities
        const localRes = await fetch('/api/pipeline/entities');
        if (localRes.ok) {
          const json = await localRes.json();
          setTools(json || []);
        } else if (fetchError) {
          throw fetchError;
        }
      }
    } catch (err) {
      console.error('Error fetching ai_tools:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTools();
  }, [fetchTools]);

  return { tools, loading, error, refetch: fetchTools };
}
