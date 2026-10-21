import { listAcademyModalities } from '@/features/modalities/api'
import { useResource } from '@/lib/hooks/useResource'

// Catálogo com is_selected; "offered" = só as que a academia oferece
export function useAcademyModalities() {
  const resource = useResource('academy-modalities', listAcademyModalities)
  const offered = (resource.data ?? []).filter((item) => item.is_selected)

  return { ...resource, offered }
}
