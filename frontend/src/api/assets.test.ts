/** Author: Dev2 | Date: 2026-07-31 | Purpose: Verify the F03 inventory API adapter contract. */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from './client'
import { exportAssets, getAssetById, getAssetLookups, getAssets, saveAsset } from './assets'

const apiAsset = {
  id: 'asset-id',
  inventory_number: 'INV-10001',
  type: { id: 'type-id', name: 'Компьютер' },
  serial_number: 'SN-10001',
  model: 'Aquarius Pro',
  purchase_date: '2026-01-15',
  status: 'in_use' as const,
  location: 'Кабинет 101',
  responsible_user: { id: 'user-id', full_name: 'Инженер Тестовый' },
  ip_address: '192.0.2.10',
  hostname: 'pc-101',
  monitoring_status: null,
  created_at: '2026-07-30T01:00:00Z',
  updated_at: '2026-07-30T02:00:00Z',
}

describe('assets API adapter', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('uses backend pagination/filter names and maps an asset list', async () => {
    const get = vi.spyOn(apiClient, 'get').mockResolvedValue({
      data: { items: [apiAsset], total: 1 },
    })

    const result = await getAssets({
      page: 2,
      pageSize: 16,
      search: 'INV-10001',
      status: 'in_use',
      typeId: 'type-id',
      location: 'Кабинет 101',
    })

    expect(get).toHaveBeenCalledWith('/api/assets', {
      params: {
        page: 2,
        page_size: 16,
        search: 'INV-10001',
        status: 'in_use',
        type_id: 'type-id',
        location: 'Кабинет 101',
      },
    })
    expect(result).toEqual({
      total: 1,
      items: [expect.objectContaining({
        id: 'asset-id',
        inventoryNumber: 'INV-10001',
        responsibleUser: { id: 'user-id', fullName: 'Инженер Тестовый' },
        movements: [],
        repairs: [],
      })],
    })
  })

  it('maps movement and repair history from the asset detail endpoint', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValue({
      data: {
        ...apiAsset,
        movements: [{
          id: 'movement-id',
          from_location: 'Склад',
          to_location: 'Кабинет 101',
          initiator: { id: 'user-id', full_name: 'Инженер Тестовый' },
          moved_at: '2026-07-30T03:00:00Z',
          comment: 'Выдано сотруднику',
        }],
        repairs: [{
          id: 'repair-id',
          repair_type: 'Диагностика',
          cost: '1500.00',
          executor: 'Сервисный центр',
          status: 'planned',
          started_at: null,
          finished_at: null,
        }],
      },
    })

    const result = await getAssetById('asset-id')

    expect(apiClient.get).toHaveBeenCalledWith('/api/assets/asset-id')
    expect(result?.movements[0]).toEqual(expect.objectContaining({
      fromLocation: 'Склад',
      initiatorName: 'Инженер Тестовый',
    }))
    expect(result?.repairs[0]).toEqual(expect.objectContaining({
      repairType: 'Диагностика',
      cost: '1500.00',
      status: 'planned',
    }))
  })

  it('loads real equipment types and derives location suggestions from assets', async () => {
    vi.spyOn(apiClient, 'get')
      .mockResolvedValueOnce({
        data: [
          { id: 'computer-type', name: 'Компьютер' },
          { id: 'printer-type', name: 'Принтер' },
        ],
      })
      .mockResolvedValueOnce({
        data: {
          items: [
            apiAsset,
            { ...apiAsset, id: 'asset-2', location: 'Склад' },
            { ...apiAsset, id: 'asset-3', location: 'Кабинет 101' },
          ],
          total: 3,
        },
      })

    const lookups = await getAssetLookups()

    expect(apiClient.get).toHaveBeenNthCalledWith(1, '/api/equipment-types')
    expect(apiClient.get).toHaveBeenNthCalledWith(2, '/api/assets', {
      params: { page: 1, page_size: 100 },
    })
    expect(lookups).toEqual({
      types: [
        { id: 'computer-type', name: 'Компьютер' },
        { id: 'printer-type', name: 'Принтер' },
      ],
      locations: ['Кабинет 101', 'Склад'],
    })
  })

  it('creates an asset and downloads a backend-generated filtered workbook', async () => {
    const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ data: apiAsset })
    vi.spyOn(apiClient, 'get')
      .mockResolvedValueOnce({ data: { ...apiAsset, movements: [], repairs: [] } })
      .mockResolvedValueOnce({ data: new Blob(['xlsx']) })

    const created = await saveAsset({
      inventoryNumber: 'INV-10001',
      typeId: 'type-id',
      serialNumber: 'SN-10001',
      model: 'Aquarius Pro',
      purchaseDate: '2026-01-15',
      status: 'in_stock',
      location: 'Кабинет 101',
    })
    const workbook = await exportAssets({
      page: 4,
      pageSize: 16,
      search: 'Aquarius',
      status: 'in_use',
    })

    expect(post).toHaveBeenCalledWith('/api/assets', {
      inventory_number: 'INV-10001',
      type_id: 'type-id',
      serial_number: 'SN-10001',
      model: 'Aquarius Pro',
      purchase_date: '2026-01-15',
      location: 'Кабинет 101',
    })
    expect(created.inventoryNumber).toBe('INV-10001')
    expect(apiClient.get).toHaveBeenLastCalledWith('/api/assets/export', {
      params: {
        status: 'in_use',
        type_id: undefined,
        location: undefined,
        search: 'Aquarius',
      },
      responseType: 'blob',
    })
    expect(workbook).toBeInstanceOf(Blob)
  })
})
