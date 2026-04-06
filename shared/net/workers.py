from PySide6.QtCore import QObject, Signal, QThread
from shared.net.api_client import ApiClient
import time


class NotificationPollingWorker(QObject):
    count_updated = Signal(int)

    def __init__(self, api_client: ApiClient):
        super().__init__()
        self.api = api_client

    

    def run(self):
        try:
            # Add a 'nocache' timestamp to force a fresh DB query every time
            t = int(time.time())
            data = self.api.get_json(f"/api/test-requests/count?status=paid&_t={t}")
            
            # Log the raw data to your console so you can see if the API is actually lying to you
            print(f"DEBUG NOTIF: Received {data}") 
            
            count = data.get("count", 0)
            self.count_updated.emit(count)
        except Exception as e:
            print(f"POLLING ERROR: {e}")
            self.count_updated.emit(0)