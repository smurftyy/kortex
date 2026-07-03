import { useQuery } from "@tanstack/react-query";

import { getMe } from "@/lib/api/endpoints";

export function useProfile() {
  return useQuery({
    queryKey: ["profile"],
    queryFn: () => getMe(),
  });
}
