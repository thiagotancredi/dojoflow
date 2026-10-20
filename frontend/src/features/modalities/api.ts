import { api } from '@/lib/api/client'
import type { ApiError, Schemas } from '@/lib/api/client'

export type ModalityOption = Schemas['ModalityOptionApiRead']

// Catálogo inteiro; is_selected diz se a academia oferece a modalidade.
// "signal" permite cancelar a requisição (ex.: o usuário saiu da tela).
export async function listAcademyModalities(
  signal?: AbortSignal,
): Promise<ModalityOption[]> {
  const { data, error } = await api.GET('/api/v1/academy/modalities', {
    signal,
  })

  if (error) {
    throw error as unknown as ApiError
  }

  return data
}

// Liga/desliga a modalidade na academia e devolve o novo estado.
export async function toggleModality(modalityId: string): Promise<boolean> {
  const { data, error } = await api.PUT(
    '/api/v1/academy/modalities/{modality_id}/toggle',
    { params: { path: { modality_id: modalityId } } },
  )

  if (error) {
    throw error as unknown as ApiError
  }

  return data.is_selected
}
