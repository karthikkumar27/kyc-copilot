from app.adapters._placeholder import PlannedProvider


class SQSQueue(PlannedProvider):
    cloud = "AWS"
    service = "Amazon SQS (or EventBridge) triggering an ECS/Lambda worker"
