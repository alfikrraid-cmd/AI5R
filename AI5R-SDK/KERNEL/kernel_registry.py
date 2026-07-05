class KernelRegistry:

    def __init__(self):
        self._kernels = {}

    def register(self, kernel):

        self._kernels[kernel.kernel_id] = kernel

        return {
            "status": "REGISTERED",
            "kernel_id": kernel.kernel_id,
        }

    def get(self, kernel_id):
        return self._kernels.get(kernel_id)

    def list_all(self):
        return list(self._kernels.values())

    def list_by_status(self, status):
        return [
            kernel
            for kernel in self._kernels.values()
            if kernel.status == status
        ]
