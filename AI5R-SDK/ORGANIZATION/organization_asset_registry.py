from typing import Dict, List, Optional
from .organization_asset import OrganizationAsset


class OrganizationAssetRegistry:
    def __init__(self):
        self.assets: Dict[str, OrganizationAsset] = {}

    def register(self, asset: OrganizationAsset) -> OrganizationAsset:
        if asset.asset_id in self.assets:
            raise ValueError("Asset already registered")

        self.assets[asset.asset_id] = asset
        return asset

    def get(self, asset_id: str) -> Optional[OrganizationAsset]:
        return self.assets.get(asset_id)

    def list_by_organization(self, organization_id: str) -> List[OrganizationAsset]:
        return [
            asset for asset in self.assets.values()
            if asset.organization_id == organization_id
        ]

    def list_by_department(self, department_id: str) -> List[OrganizationAsset]:
        return [
            asset for asset in self.assets.values()
            if asset.department_id == department_id
        ]

    def list_by_owner_worker(self, worker_id: str) -> List[OrganizationAsset]:
        return [
            asset for asset in self.assets.values()
            if asset.owner_worker_id == worker_id
        ]

    def find_by_type(self, asset_type: str) -> List[OrganizationAsset]:
        return [
            asset for asset in self.assets.values()
            if asset.asset_type == asset_type
        ]
