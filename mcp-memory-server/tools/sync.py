# -*- coding: utf-8 -*-
from datetime import datetime, timezone
import platform
import socket


class SyncTool:
    """Multi-device sync via Firebase"""

    def __init__(self, firebase_client, user_id: str):
        self.firebase = firebase_client
        self.user_id = user_id

    def _get_device_info(self, device_id: str) -> dict:
        return {
            "device_id": device_id,
            "hostname": socket.gethostname(),
            "platform": platform.system(),
            "platform_version": platform.version()[:50],
            "last_seen": datetime.now(timezone.utc).isoformat()
        }

    async def execute(self, args: dict) -> dict:
        device_id = args.get("device_id", socket.gethostname())
        push = args.get("push", False)

        device_info = self._get_device_info(device_id)

        if push:
            self.firebase.update_device_sync(self.user_id, device_id, device_info)

        all_devices = self.firebase.get_all_device_states(self.user_id)

        # Find latest activity from other devices
        other_devices = [d for d in all_devices if d.get("device_id") != device_id]

        return {
            "success": True,
            "current_device": device_id,
            "registered_devices": len(all_devices),
            "other_devices": [
                {
                    "device_id": d.get("device_id"),
                    "hostname": d.get("hostname"),
                    "platform": d.get("platform"),
                    "last_seen": str(d.get("last_seen", ""))
                }
                for d in other_devices
            ],
            "sync_status": "pushed" if push else "pulled"
        }
