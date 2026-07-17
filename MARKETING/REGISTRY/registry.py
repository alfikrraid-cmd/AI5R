class MarketingRegistry:
    def __init__(self):
        self.items = {}

    def register(self, artifact_id, artifact):
        self.items[artifact_id] = artifact
        return artifact_id

    def get(self, artifact_id):
        return self.items.get(artifact_id)
