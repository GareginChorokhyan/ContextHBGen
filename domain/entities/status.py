class Status:
    def __init__(self):
        self.status = "new"

    def get_status(self):
        return self.status

    def mark_as_ingested(self):
        self.status = "ingested"

    def mark_as_processed(self):
        self.status = "processed"

    def mark_as_failed(self):
        self.status = "failed"
