import os
from typing import List

from langchain.tools import tool
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from shoppinggpt.config import get_embeddings, DATA_TEXT_PATH, STORE_DIRECTORY


class VectorStoreManager:
    _instance = None

    def __init__(self, data_path: str, store_directory: str, embeddings):
        self.data_path = data_path
        self.store_directory = store_directory
        self.embeddings = embeddings
        self.vectorstore = self._load_or_create()

    @classmethod
    def get_instance(cls, data_path: str, store_directory: str, embeddings):
        if cls._instance is None:
            cls._instance = cls(data_path, store_directory, embeddings)
        return cls._instance

    def _load_or_create(self):
        index_path = os.path.join(self.store_directory, "index.faiss")
        if os.path.exists(index_path):
            return FAISS.load_local(
                self.store_directory,
                self.embeddings,
                allow_dangerous_deserialization=True,
            )
        return self._create_vectorstore()

    def _create_vectorstore(self):
        loader = TextLoader(self.data_path, encoding="utf8")
        documents = loader.load()
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=150,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        chunks = splitter.split_documents(documents)
        vectorstore = FAISS.from_documents(chunks, self.embeddings)
        os.makedirs(self.store_directory, exist_ok=True)
        vectorstore.save_local(self.store_directory)
        return vectorstore


@tool
def policy_search_tool(query: str) -> List[str]:
    """Search store policies for information about shipping, returns, payments, accounts, and other customer service topics.

    Args:
        query: The customer question about store policies.

    Returns:
        List of relevant policy excerpts.
    """
    manager = VectorStoreManager.get_instance(
        DATA_TEXT_PATH, STORE_DIRECTORY, get_embeddings()
    )
    results = manager.vectorstore.similarity_search(query, k=5)
    return [doc.page_content for doc in results]
