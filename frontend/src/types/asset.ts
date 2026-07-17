/** Author: Dev2 | Date: 2026-07-16 | Purpose: Inventory contracts shaped for the future assets API. */
export type AssetStatus = 'in_use' | 'repair' | 'written_off' | 'in_stock'

export interface AssetType {
  id: string
  name: string
}

export interface ResponsibleUser {
  id: string
  fullName: string
}

export interface Movement {
  id: string
  fromLocation?: string
  toLocation: string
  initiatorName: string
  movedAt: string
  comment?: string
}

export interface Repair {
  id: string
  openedAt: string
  closedAt?: string
  description: string
  result?: string
}

export interface Asset {
  id: string
  inventoryNumber: string
  type: AssetType
  serialNumber?: string
  model?: string
  purchaseDate?: string
  status: AssetStatus
  location?: string
  responsibleUser?: ResponsibleUser
  ipAddress?: string
  hostname?: string
  createdAt: string
  updatedAt: string
  movements: Movement[]
  repairs: Repair[]
}

export interface AssetFilters {
  page: number
  pageSize: number
  search?: string
  status?: AssetStatus
  typeId?: string
  location?: string
  responsibleUserId?: string
}

export interface AssetListResponse {
  items: Asset[]
  total: number
}

export interface AssetFormValues {
  inventoryNumber: string
  typeId: string
  serialNumber?: string
  model?: string
  purchaseDate?: string
  status: AssetStatus
  location?: string
  responsibleName?: string
  ipAddress?: string
  hostname?: string
}
