from utils.chroma_db import ChromaDB
import logging
import os

logging.basicConfig(level=logging.INFO)


class DocumentIngester:
    def __init__(self):
        self.chroma_db = ChromaDB()
        self.chroma_db.initiate_collection()

    def ingest_documents(self, documents, prefixes=None):

        for i, document in enumerate(documents):
            prefix = prefixes[i] if prefixes and i < len(prefixes) else "doc"
            self.chroma_db.add_to_knowledge_base(document, key_prefix=prefix)

    def ingest_files(self, file_paths, prefixes=None):
        documents = []
        for file_path in file_paths:
            with open(file_path, "r") as file:
                documents.append(file.read())
        self.ingest_documents(documents, prefixes)

    def ingest_files_from_directory(self, directory_path, prefixes=None):
        file_paths = [
            os.path.join(directory_path, file)
            for file in os.listdir(directory_path)
            if file.endswith(".txt")
        ]
        self.ingest_files(file_paths, prefixes)


if __name__ == "__main__":
    document_ingester = DocumentIngester()
    document_ingester.ingest_files_from_directory(
        "../data/docs", ["general", "insurance"]
    )
