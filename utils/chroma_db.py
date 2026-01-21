import chromadb
import logging
import os

logging.basicConfig(level=logging.INFO)


class ChromaDB:
    def __init__(self):
        self.initialize_client()
        self.initiate_collection()

    def initiate_collection(self):

        if self.client is None:
            self.initialize_client()

        self.collection = self.client.get_or_create_collection(
            name="office-data"
        )

        logging.info("Collection created")

    def initialize_client(self):

        self.client = chromadb.CloudClient(
            api_key=os.environ.get("CHROMA_API_KEY"),
            tenant=os.environ.get("CHROMA_TENANT_ID"),
            database=os.environ.get("CHROMA_DB"),
        )
        logging.info("Client initialized")

    def get_client(self):

        if self.client is None:
            self.initialize_client()

        return self.client

    def search_knowledge_base(self, query, n_results=5):

        results = self.collection.query(query_texts=query, n_results=n_results)
        logging.debug(f"Search results: {results}")

        if "documents" not in results or len(results["documents"]) == 0:
            logging.info("No documents found for the given query.")
            return None

        return results["documents"][0]

    def add_to_knowledge_base(self, document, doc_id="doc"):

        self.collection.add(ids=[doc_id], documents=[document])

        logging.info("Document added to knowledge base")

    def add_to_knowledge_base_from_directory(self, directory_path):
        file_paths = [
            os.path.join(directory_path, file)
            for file in os.listdir(directory_path)
            if file.endswith(".txt")
        ]

        documents = []
        for file_path in file_paths:
            with open(file_path, "r") as file:
                documents.append(file.read())

        # file names as prefixes
        prefixes = [os.path.basename(file_path) for file_path in file_paths]

        for i, document in enumerate(documents):
            self.add_to_knowledge_base(document, doc_id=prefixes[i])


if __name__ == "__main__":
    chroma_db = ChromaDB()
    chroma_db.initiate_collection()
    chroma_db.add_to_knowledge_base_from_directory("../data")
