import { create } from "zustand";

interface Profile {
  id: string;
  full_name: string;
  artistic_name?: string;
  status: string;
  photoshoot_count: number;
}

interface ProfileState {
  profiles: Profile[];
  selectedProfile: Profile | null;
  setProfiles: (profiles: Profile[]) => void;
  addProfile: (profile: Profile) => void;
  selectProfile: (profile: Profile | null) => void;
}

export const useProfileStore = create<ProfileState>((set) => ({
  profiles: [],
  selectedProfile: null,
  setProfiles: (profiles) => set({ profiles }),
  addProfile: (profile) => set((state) => ({ profiles: [...state.profiles, profile] })),
  selectProfile: (profile) => set({ selectedProfile: profile }),
}));
