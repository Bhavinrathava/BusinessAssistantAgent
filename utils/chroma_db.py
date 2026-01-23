import chromadb
import logging
import streamlit as st
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

        # Try st.secrets first (Streamlit Cloud), fall back to os.getenv (local)
        api_key = st.secrets.get("CHROMA_API_KEY") or os.getenv(
            "CHROMA_API_KEY"
        )
        tenant_id = st.secrets.get("CHROMA_TENANT_ID") or os.getenv(
            "CHROMA_TENANT_ID"
        )
        database = st.secrets.get("CHROMA_DB") or os.getenv("CHROMA_DB")

        self.client = chromadb.CloudClient(
            api_key=api_key,
            tenant=tenant_id,
            database=database,
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

    def get_all_documents(self):
        """Retrieve all documents from the collection."""
        results = self.collection.get()
        if not results or "ids" not in results:
            return []

        documents = []
        for i, doc_id in enumerate(results["ids"]):
            doc_content = results["documents"][i] if results["documents"] else ""
            documents.append({"id": doc_id, "content": doc_content})

        return documents

    def delete_document(self, doc_id):
        """Delete a document from the collection by its ID."""
        self.collection.delete(ids=[doc_id])
        logging.info(f"Document '{doc_id}' deleted from knowledge base")

    def update_document(self, doc_id, new_content):
        """Update a document by deleting the old one and adding the new content."""
        self.delete_document(doc_id)
        self.add_to_knowledge_base(new_content, doc_id)
        logging.info(f"Document '{doc_id}' updated in knowledge base")

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
