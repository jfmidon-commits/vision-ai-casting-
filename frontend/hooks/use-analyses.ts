import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { analysisApi } from "@/lib/api";
import { Analysis } from "@/types";

export function useAnalyses(params?: any) {
  return useQuery({
    queryKey: ["analyses", params],
    queryFn: async () => {
      const res = await analysisApi.list(params);
      return res.data.data as Analysis[];
    },
  });
}

export function useStartAnalysis() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ photoshootId, data }: { photoshootId: string; data: any }) =>
      analysisApi.start(photoshootId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["analyses"] });
    },
  });
}
