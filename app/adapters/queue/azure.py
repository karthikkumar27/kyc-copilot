from app.adapters._placeholder import PlannedProvider


class ServiceBusQueue(PlannedProvider):
    cloud = "Azure"
    service = "Azure Service Bus (or Storage Queues) triggering a Container Apps job"
