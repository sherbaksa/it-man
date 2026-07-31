/** Author: Dev2 | Date: 2026-07-31 | Purpose: Real backend adapter for the inventory API. */
import { apiClient } from './client'
import type { components } from './types'
import type {
  Asset,
  AssetFilters,
  AssetFormValues,
  AssetListResponse,
  AssetLookups,
  AssetStatus,
  Movement,
  Repair,
} from '../types/asset'

type ApiAssetCreate = components['schemas']['AssetCreate']
type ApiAssetDetail = components['schemas']['AssetDetail']
type ApiAssetListResponse = components['schemas']['AssetListResponse']
type ApiAssetRead = components['schemas']['AssetRead']
type ApiAssetUpdate = components['schemas']['AssetUpdate']
type ApiEquipmentType = components['schemas']['EquipmentTypeRead']
type ApiMovement = components['schemas']['MovementBrief']
type ApiRepair = components['schemas']['RepairBrief']

export const assetStatusLabels: Record<AssetStatus, string> = {
  in_use: 'В работе',
  repair: 'В ремонте',
  written_off: 'Списано',
  in_stock: 'На складе',
}

function mapMovement(item: ApiMovement): Movement {
  return {
    id: item.id,
    fromLocation: item.from_location ?? undefined,
    toLocation: item.to_location,
    initiatorName: item.initiator.full_name,
    movedAt: item.moved_at,
    comment: item.comment ?? undefined,
  }
}

function mapRepair(item: ApiRepair): Repair {
  return {
    id: item.id,
    repairType: item.repair_type,
    cost: item.cost ?? undefined,
    executor: item.executor ?? undefined,
    status: item.status,
    startedAt: item.started_at ?? undefined,
    finishedAt: item.finished_at ?? undefined,
  }
}

function mapAsset(item: ApiAssetRead | ApiAssetDetail): Asset {
  const detail = item as ApiAssetDetail
  return {
    id: item.id,
    inventoryNumber: item.inventory_number,
    type: item.type,
    serialNumber: item.serial_number ?? undefined,
    model: item.model ?? undefined,
    purchaseDate: item.purchase_date ?? undefined,
    status: item.status,
    location: item.location ?? undefined,
    responsibleUser: item.responsible_user
      ? { id: item.responsible_user.id, fullName: item.responsible_user.full_name }
      : undefined,
    ipAddress: item.ip_address ?? undefined,
    hostname: item.hostname ?? undefined,
    monitoringStatus: item.monitoring_status?.status,
    createdAt: item.created_at,
    updatedAt: item.updated_at,
    movements: detail.movements?.map(mapMovement) ?? [],
    repairs: detail.repairs?.map(mapRepair) ?? [],
  }
}

function toQuery(filters: AssetFilters, includePagination = true) {
  return {
    status: filters.status,
    type_id: filters.typeId,
    location: filters.location,
    search: filters.search?.trim() || undefined,
    ...(includePagination ? { page: filters.page, page_size: filters.pageSize } : {}),
  }
}

export async function getAssets(filters: AssetFilters): Promise<AssetListResponse> {
  const { data } = await apiClient.get<ApiAssetListResponse>('/api/assets', {
    params: toQuery(filters),
  })
  return { items: data.items.map(mapAsset), total: data.total }
}

export async function getAssetById(id?: string): Promise<Asset | undefined> {
  if (!id) return undefined
  const { data } = await apiClient.get<ApiAssetDetail>(`/api/assets/${id}`)
  return mapAsset(data)
}

export async function saveAsset(values: AssetFormValues, id?: string): Promise<Asset> {
  const commonFields = {
    inventory_number: values.inventoryNumber.trim(),
    type_id: values.typeId,
    serial_number: values.serialNumber?.trim() || null,
    model: values.model?.trim() || null,
    purchase_date: values.purchaseDate || null,
    location: values.location?.trim() || null,
  }

  if (id) {
    const payload: ApiAssetUpdate = {
      ...commonFields,
      status: values.status,
      ip_address: values.ipAddress?.trim() || null,
      hostname: values.hostname?.trim() || null,
    }
    const { data } = await apiClient.patch<ApiAssetDetail>(`/api/assets/${id}`, payload)
    return mapAsset(data)
  }

  const createPayload: ApiAssetCreate = commonFields
  const { data: created } = await apiClient.post<ApiAssetRead>('/api/assets', createPayload)
  const needsFollowUp = values.status !== 'in_stock' || Boolean(values.ipAddress?.trim()) || Boolean(values.hostname?.trim())

  if (needsFollowUp) {
    const payload: ApiAssetUpdate = {
      status: values.status,
      ip_address: values.ipAddress?.trim() || null,
      hostname: values.hostname?.trim() || null,
    }
    const { data } = await apiClient.patch<ApiAssetDetail>(`/api/assets/${created.id}`, payload)
    return mapAsset(data)
  }

  return (await getAssetById(created.id)) ?? mapAsset(created)
}

export async function getAssetLookups(): Promise<AssetLookups> {
  const [{ data: types }, { data: assets }] = await Promise.all([
    apiClient.get<ApiEquipmentType[]>('/api/equipment-types'),
    apiClient.get<ApiAssetListResponse>('/api/assets', {
      params: { page: 1, page_size: 100 },
    }),
  ])
  const locations = Array.from(
    new Set(assets.items.map((item) => item.location).filter((value): value is string => Boolean(value))),
  ).sort((left, right) => left.localeCompare(right, 'ru'))
  return {
    types,
    locations,
  }
}

export async function exportAssets(filters: AssetFilters): Promise<Blob> {
  const { data } = await apiClient.get<Blob>('/api/assets/export', {
    params: toQuery(filters, false),
    responseType: 'blob',
  })
  return data
}
