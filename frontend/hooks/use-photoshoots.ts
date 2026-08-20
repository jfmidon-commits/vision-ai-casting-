import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { photoshootApi } from "@/lib/api";
import { Photo, Photoshoot } from "@/types";

export function usePhotoshoots(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: ["photoshoots", params],
    queryFn: async () => {
      const response = await photoshootApi.list(params);
      return response.data.data as Photoshoot[];
    },
  });
}

export function usePhotoshoot(id?: string) {
  return useQuery({
    queryKey: ["photoshoot", id],
    enabled: Boolean(id),
    queryFn: async () => {
      const response = await photoshootApi.get(id as string);
      return response.data.data as Photoshoot;
    },
  });
}

export function usePhotoshootPhotos(id?: string) {
  return useQuery({
    queryKey: ["photoshoot-photos", id],
    enabled: Boolean(id),
    queryFn: async () => {
      const response = await photoshootApi.listPhotos(id as string);
      return response.data.data as Photo[];
    },
  });
}

export function useCreatePhotoshoot() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => photoshootApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["photoshoots"] });
    },
  });
}

export function useUploadPhotos(photoshootId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ files, angle }: { files: File[]; angle: string }) =>
      Promise.all(
        files.map((file) => photoshootApi.uploadPhoto(photoshootId, file, angle))
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["photoshoot", photoshootId] });
      queryClient.invalidateQueries({ queryKey: ["photoshoot-photos", photoshootId] });
      queryClient.invalidateQueries({ queryKey: ["photoshoots"] });
    },
  });
}
