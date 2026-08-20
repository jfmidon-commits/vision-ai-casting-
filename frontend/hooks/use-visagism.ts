import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { visagismApi } from "@/lib/api";
import { FullVisagismAnalysis } from "@/types";

export function useStartVisagism() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      photoshootId,
      cutLimit = 5,
      generateCard = true,
    }: {
      photoshootId: string;
      cutLimit?: number;
      generateCard?: boolean;
    }) => visagismApi.analyze(photoshootId, cutLimit, generateCard),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["analyses"] });
    },
  });
}

export function useVisagismResult(analysisId?: string) {
  return useQuery({
    queryKey: ["visagism", analysisId],
    enabled: Boolean(analysisId),
    queryFn: async () => {
      const response = await visagismApi.getResult(analysisId as string);
      return response.data.data as FullVisagismAnalysis | null;
    },
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "completed" || status === "failed" ? false : 2500;
    },
  });
}
