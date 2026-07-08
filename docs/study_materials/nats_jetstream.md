# NATS: Comprehensive Reference Guide

NATS is a connective technology. Unlike traditional message brokers that focus on "guaranteed delivery at any cost," NATS focuses on **high performance, simplicity, and low latency**. It acts as a digital nervous system for distributed systems.

---

## 1. Introduction to NATS
NATS operates on the **Publish-Subscribe** pattern, which decouples producers of data from consumers. It is highly optimized for cloud-native applications, IoT, and microservices.

---

## 2. Setting Up (Python)
First, ensure you have a NATS server running. The easiest way is via Docker:

```bash
docker run -p 4222:4222 nats:latest
```

Install the Python client:

```bash
pip install nats-py
```

---

## 3. Core Messaging Patterns

### A. Publish-Subscribe (Pub/Sub)
This is "fire-and-forget." The publisher sends a message, and all active subscribers receive it. If no one is listening, the message is dropped.

**Publisher:**
```python
import asyncio
from nats.aio.client import Client as NATS

async def main():
    nc = NATS()
    await nc.connect("nats://localhost:4222")
    
    # Simple publish
    await nc.publish("updates.sensors", b"Temperature: 22C")
    await nc.close()

if __name__ == '__main__':
    asyncio.run(main())
```

**Subscriber:**
```python
async def subscribe_updates():
    nc = NATS()
    await nc.connect("nats://localhost:4222")

    async def message_handler(msg):
        print(f"Received: {msg.data.decode()} on subject {msg.subject}")

    # Using wildcards to subscribe
    await nc.subscribe("updates.>", cb=message_handler)
```

---

## 4. Advanced Patterns

### B. Request-Reply (The "RPC" Pattern)
NATS allows you to send a message and synchronously wait for a response. The NATS server handles the creation of a unique "reply subject" automatically.

**Requester:**
```python
# Send a request and wait for a reply
msg = await nc.request("get.system.status", b"PING", timeout=1)
print(f"Reply received: {msg.data.decode()}")
```

**Responder:**
```python
async def handler(msg):
    # Process request and respond
    await msg.respond(b"System Status: OK")

await nc.subscribe("get.system.status", cb=handler)
```

### C. Queue Groups (Load Balancing)
If you have multiple workers, you don't want every worker to process every message. By using a **Queue Group**, NATS will distribute messages to only *one* member of the group.

```python
# All subscribers with the same queue name share the load
await nc.subscribe("tasks", queue="workers", cb=handler)
```

---

## 5. NATS JetStream (Persistence)
Core NATS is transient. If a subscriber is offline, it misses the message. **JetStream** adds a layer of persistence on top of NATS.

1. **Streams:** Define a subject to be persisted (e.g., `orders.>`).
2. **Consumers:** Define how to read the stream (e.g., pull mode for batch processing).

---

## 6. Important Architectural Rules
* **Hierarchical Subjects:** Use dots (`.`) to organize namespaces (e.g., `org.region.app.component`).
* **Wildcards:**
    * `*`: Matches exactly one token (`updates.*.status` matches `updates.us.status`).
    * `>`: Matches one or more tokens at the end (`updates.>` matches `updates.us.east.status`).
* **Performance:** NATS is extremely fast. Avoid putting large objects in messages; keep payloads small and use binary formats (Protobuf/JSON) if necessary.

---

## 7. Summary Cheat Sheet

| Feature | Pattern | Use Case |
| :--- | :--- | :--- |
| **Pub/Sub** | `publish` | Broadcast, Event notifications. |
| **Req/Reply** | `request` | Microservice communication, RPC. |
| **Queue** | `queue` | Load balancing, Task distribution. |
| **JetStream** | `streams` | Persistent messaging, Auditing, Replay. |
