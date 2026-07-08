import asyncio
import nats

async def error_callback(error):
    """Called when an error occurs on the connection"""
    print(f"Connection error: {error}")

async def disconnected_callback():
    """Called when client disconnects from server"""
    print("Disconnected from NATS")

async def reconnected_callback():
    """Called when client reconnects after a disconnect"""
    print("Reconnected to NATS")

async def closed_callback():
    """Called when connection is permanently closed"""
    print("Connection to NATS closed")

async def main():
    # Connect with comprehensive options for production reliability
    nc = await nats.connect(
        servers=[
            "nats://localhost:4222",  # Primary server
            "nats://localhost:4223",  # Backup server 1
            "nats://localhost:4224",  # Backup server 2
        ],
        # Reconnection settings - automatically reconnect on failure
        allow_reconnect=True,
        max_reconnect_attempts=10,  # -1 for unlimited attempts
        reconnect_time_wait=5,  # Seconds between reconnection attempts

        # Connection timeouts
        connect_timeout=5,  # Seconds to wait for initial connection

        # Ping/pong for connection health monitoring
        ping_interval=20,  # Send ping every 20 seconds
        max_outstanding_pings=3,  # Disconnect if 3 pings go unanswered

        # Callbacks for connection lifecycle events
        error_cb=error_callback,
        disconnected_cb=disconnected_callback,
        reconnected_cb=reconnected_callback,
        closed_cb=closed_callback,

        # Optional authentication
        # user="myuser",
        # password="mypassword",
        # token="mytoken",
    )

    print(f"Connected to {nc.connected_url.netloc}")

    # Keep connection alive for demonstration
    await asyncio.sleep(5)
    await nc.drain()  # Graceful shutdown - wait for pending messages
if __name__ == "__main__":
    asyncio.run(main())

#