import json

class Repo:
    def __init__(self, slug: str, label: str, category: str, username: str):
        self.slug = slug
        self.label = label
        self.category = category
        self.username = username