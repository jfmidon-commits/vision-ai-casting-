import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { profileApi } from "@/lib/api";
import { Profile } from "@/types";

export function useProfiles(params?: any) {
  return useQuery({
    queryKey: ["profiles", params],
    queryFn: async () => {
      const res = await profileApi.list(params);
      return res.data.data as Profile[];
    },
  });
}

export function useProfile(id: string) {
  return useQuery({
    queryKey: ["profile", id],
    queryFn: async () => {
      const res = await profileApi.get(id);
      return res.data.data as Profile;
    },
    enabled: !!id,
  });
}

export function useCreateProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: profileApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profiles"] });
    },
  });
}
