async def publish_event(event_name: str, payload: dict):
    # This is a mock function. Implement RabbitMQ / actual broker logic here.
    print(f"Event published: {event_name} -> {payload}")
