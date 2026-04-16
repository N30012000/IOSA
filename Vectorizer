"""
Vector Database Module
Handles embedding generation and semantic search for compliance documents
"""

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from loguru import logger
import pickle
from dataclasses import asdict

from app.config import settings
from app.utils.pdf_parser import DocumentChunk, ISARPRequirement


class VectorStore:
    """Vector database manager for semantic search"""
    
    def __init__(self, db_path: Optional[Path] = None, embedding_model: Optional[str] = None):
        self.db_path = db_path or settings.vector_db_path
        self.embedding_model_name = embedding_model or settings.embedding_model
        
        # Initialize embedding model
        logger.info(f"Loading embedding model: {self.embedding_model_name}")
        self.embedding_model = SentenceTransformer(self.embedding_model_name)
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        
        # Create collections
        self.ism_collection = self._get_or_create_collection("ism_standards")
        self.manuals_collection = self._get_or_create_collection("airline_manuals")
        self.evidence_collection = self._get_or_create_collection("evidence_documents")
    
    def _get_or_create_collection(self, name: str):
        """Get existing collection or create new one"""
        try:
            collection = self.client.get_collection(name)
            logger.info(f"Loaded existing collection: {name}")
        except:
            collection = self.client.create_collection(
                name=name,
                metadata={"description": f"Collection for {name}"}
            )
            logger.info(f"Created new collection: {name}")
        
        return collection
    
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts"""
        embeddings = self.embedding_model.encode(
            texts,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        return embeddings
    
    def add_ism_chunks(self, chunks: List[DocumentChunk], isarp_code: Optional[str] = None):
        """Add ISM document chunks to vector database"""
        if not chunks:
            logger.warning("No chunks to add to ISM collection")
            return
        
        # Generate embeddings
        texts = [chunk.text for chunk in chunks]
        embeddings = self.generate_embeddings(texts)
        
        # Prepare data for ChromaDB
        ids = [f"ism_{chunk.source_file}_{chunk.chunk_index}" for chunk in chunks]
        metadatas = []
        
        for chunk in chunks:
            metadata = {
                "source_file": chunk.source_file,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
                "document_type": "ISM"
            }
            if isarp_code:
                metadata["isarp_code"] = isarp_code
            
            metadatas.append(metadata)
        
        # Add to collection
        self.ism_collection.add(
            embeddings=embeddings.tolist(),
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        
        logger.info(f"Added {len(chunks)} ISM chunks to vector database")
    
    def add_manual_chunks(self, chunks: List[DocumentChunk], manual_type: str, manual_name: str):
        """Add airline manual chunks to vector database"""
        if not chunks:
            logger.warning("No chunks to add to manuals collection")
            return
        
        # Generate embeddings
        texts = [chunk.text for chunk in chunks]
        embeddings = self.generate_embeddings(texts)
        
        # Prepare data
        ids = [f"manual_{manual_name}_{chunk.chunk_index}" for chunk in chunks]
        metadatas = [
            {
                "source_file": chunk.source_file,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
                "manual_type": manual_type,
                "manual_name": manual_name,
                "document_type": "MANUAL"
            }
            for chunk in chunks
        ]
        
        # Add to collection
        self.manuals_collection.add(
            embeddings=embeddings.tolist(),
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        
        logger.info(f"Added {len(chunks)} manual chunks to vector database")
    
    def add_evidence_document(self, chunks: List[DocumentChunk], isarp_code: str, 
                            evidence_type: str):
        """Add evidence document chunks linked to specific ISARP"""
        if not chunks:
            logger.warning("No chunks to add to evidence collection")
            return
        
        # Generate embeddings
        texts = [chunk.text for chunk in chunks]
        embeddings = self.generate_embeddings(texts)
        
        # Prepare data
        ids = [f"evidence_{isarp_code}_{chunk.source_file}_{chunk.chunk_index}" 
               for chunk in chunks]
        metadatas = [
            {
                "source_file": chunk.source_file,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
                "isarp_code": isarp_code,
                "evidence_type": evidence_type,
                "document_type": "EVIDENCE"
            }
            for chunk in chunks
        ]
        
        # Add to collection
        self.evidence_collection.add(
            embeddings=embeddings.tolist(),
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        
        logger.info(f"Added {len(chunks)} evidence chunks for {isarp_code}")
    
    def search_manuals(self, query: str, top_k: int = 5, 
                      manual_type: Optional[str] = None) -> List[Dict]:
        """
        Search airline manuals for relevant passages
        
        Args:
            query: Search query (usually ISARP requirement text)
            top_k: Number of results to return
            manual_type: Filter by manual type (e.g., "Flight Operations Manual")
        
        Returns:
            List of relevant passages with metadata
        """
        # Generate query embedding
        query_embedding = self.generate_embeddings([query])[0]
        
        # Build filter
        where_filter = None
        if manual_type:
            where_filter = {"manual_type": manual_type}
        
        # Search
        results = self.manuals_collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k,
            where=where_filter
        )
        
        # Format results
        formatted_results = []
        if results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    "text": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i] if 'distances' in results else None,
                    "similarity": 1 - results['distances'][0][i] if 'distances' in results else None
                })
        
        return formatted_results
    
    def search_evidence(self, isarp_code: str, top_k: int = 3) -> List[Dict]:
        """Search for evidence documents linked to specific ISARP"""
        results = self.evidence_collection.query(
            query_embeddings=None,
            n_results=top_k,
            where={"isarp_code": isarp_code}
        )
        
        formatted_results = []
        if results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    "text": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i]
                })
        
        return formatted_results
    
    def hybrid_search(self, isarp_requirement: ISARPRequirement, 
                     top_k: int = 5) -> List[Dict]:
        """
        Perform hybrid search combining:
        1. Semantic similarity (vector search)
        2. Keyword matching (for specific terms like ISARP code)
        3. Category filtering (search in relevant manual types)
        """
        # Determine which manual types are most relevant
        category_to_manual_map = {
            "ORG": ["Company Operations Manual", "Safety Management System Manual"],
            "FLT": ["Flight Operations Manual", "Flight Crew Operating Manual"],
            "MNT": ["Aircraft Maintenance Manual"],
            "GRH": ["Ground Handling Manual"],
            "CGO": ["Ground Handling Manual", "Dangerous Goods Manual"],
            "SEC": ["Security Manual"],
            "DSP": ["Dangerous Goods Manual"]
        }
        
        relevant_manuals = category_to_manual_map.get(
            isarp_requirement.category, 
            None  # Search all if not found
        )
        
        all_results = []
        
        # Search each relevant manual type
        if relevant_manuals:
            for manual_type in relevant_manuals:
                results = self.search_manuals(
                    query=isarp_requirement.requirement_text,
                    top_k=top_k,
                    manual_type=manual_type
                )
                all_results.extend(results)
        else:
            # Search all manuals
            results = self.search_manuals(
                query=isarp_requirement.requirement_text,
                top_k=top_k
            )
            all_results.extend(results)
        
        # Sort by similarity and return top_k
        all_results.sort(key=lambda x: x.get('similarity', 0), reverse=True)
        return all_results[:top_k]
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about collections"""
        return {
            "ism_count": self.ism_collection.count(),
            "manuals_count": self.manuals_collection.count(),
            "evidence_count": self.evidence_collection.count()
        }
    
    def clear_collection(self, collection_name: str):
        """Clear a specific collection"""
        try:
            self.client.delete_collection(collection_name)
            logger.info(f"Cleared collection: {collection_name}")
            
            # Recreate empty collection
            if collection_name == "ism_standards":
                self.ism_collection = self._get_or_create_collection(collection_name)
            elif collection_name == "airline_manuals":
                self.manuals_collection = self._get_or_create_collection(collection_name)
            elif collection_name == "evidence_documents":
                self.evidence_collection = self._get_or_create_collection(collection_name)
        except Exception as e:
            logger.error(f"Error clearing collection {collection_name}: {e}")


class SemanticMatcher:
    """Advanced semantic matching utilities"""
    
    @staticmethod
    def calculate_similarity(text1: str, text2: str, model: SentenceTransformer) -> float:
        """Calculate cosine similarity between two texts"""
        embeddings = model.encode([text1, text2])
        
        # Cosine similarity
        similarity = np.dot(embeddings[0], embeddings[1]) / (
            np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
        )
        
        return float(similarity)
    
    @staticmethod
    def find_keyword_matches(requirement_text: str, manual_text: str) -> List[str]:
        """Find specific keywords from requirement that appear in manual"""
        # Extract important keywords (shall, must, required, etc.)
        important_keywords = settings.finding_keywords
        
        found_keywords = []
        requirement_lower = requirement_text.lower()
        manual_lower = manual_text.lower()
        
        for keyword in important_keywords:
            if keyword in requirement_lower and keyword in manual_lower:
                found_keywords.append(keyword)
        
        return found_keywords
    
    @staticmethod
    def extract_numeric_requirements(text: str) -> List[str]:
        """Extract numeric requirements (e.g., '30 days', '5 years', '100 meters')"""
        import re
        pattern = r'\b\d+\s*(?:days?|months?|years?|hours?|meters?|feet|percent|%)\b'
        matches = re.findall(pattern, text.lower())
        return matches
