import os
import json
import logging
from typing import List, Dict, Any
from datetime import datetime
import torch
from FlagEmbedding import BGEM3FlagModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmbeddingProcessor:
    def __init__(self):
        self.model_name = os.environ['EMBEDDING_MODEL']
        self.chunk_size = int(os.environ['CHUNK_SIZE'])
        self.chunk_overlap = int(os.environ['CHUNK_OVERLAP'])
        self.batch_size = int(os.environ['EMBEDDING_BATCH_SIZE'])
        self.use_cuda = os.environ['USE_CUDA'].lower() == 'true'
        
        # Initialize model
        self.device = 'cuda' if self.use_cuda and torch.cuda.is_available() else 'cpu'
        logger.info(f"Initializing BGE-M3 model on {self.device}")
        
        try:
            self.model = BGEM3FlagModel(self.model_name, use_fp16=self.use_cuda)
            logger.info(f"Model {self.model_name} loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks
        
        Args:
            text: Input text to chunk
        
        Returns:
            List of text chunks
        """
        if not text:
            return []
        
        chunks = []
        words = text.split()
        
        if len(words) <= self.chunk_size:
            return [text]
        
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk = ' '.join(chunk_words)
            chunks.append(chunk)
            
            # Stop if we've processed all words
            if i + self.chunk_size >= len(words):
                break
        
        return chunks
    
    def prepare_product_text(self, product: Dict[str, Any]) -> str:
        """Prepare product data as text for embedding
        
        Args:
            product: Product dictionary with fields
        
        Returns:
            Formatted text string
        """
        text_parts = []
        
        # Add product name
        if product.get('name'):
            text_parts.append(f"Product Name: {product['name']}")
        
        # Add price
        if product.get('price'):
            text_parts.append(f"Price: {product['price']}")
        
        # Add material
        if product.get('material'):
            text_parts.append(f"Material: {product['material']}")
        
        # Add features
        if product.get('features'):
            text_parts.append(f"Features: {product['features']}")
        
        # Add description
        if product.get('description'):
            text_parts.append(f"Description: {product['description']}")
        
        # Parse and add JSON data if available
        if product.get('product_data'):
            try:
                json_data = json.loads(product['product_data'])
                
                # Add product info
                if 'product_info' in json_data:
                    info = json_data['product_info']
                    for key, value in info.items():
                        if value and key not in ['name', 'price']:
                            text_parts.append(f"{key.replace('_', ' ').title()}: {value}")
                
                # Add details
                if 'details' in json_data:
                    for detail in json_data['details']:
                        if detail:
                            text_parts.append(f"Detail: {detail}")
                
                # Add spec items
                if 'spec_items' in json_data:
                    for spec in json_data['spec_items']:
                        if spec:
                            text_parts.append(f"Specification: {spec}")
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse product_data JSON for product {product.get('id')}")
        
        # Combine all parts
        full_text = " | ".join(text_parts)
        return full_text
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts
        
        Args:
            texts: List of text strings
        
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        try:
            # Process in batches
            all_embeddings = []
            
            for i in range(0, len(texts), self.batch_size):
                batch_texts = texts[i:i + self.batch_size]
                
                # Generate embeddings using BGE-M3
                embeddings = self.model.encode(
                    batch_texts,
                    batch_size=len(batch_texts),
                    max_length=8192
                )['dense_vecs']
                
                # Convert to list and extend
                all_embeddings.extend(embeddings.tolist())
            
            logger.info(f"Generated {len(all_embeddings)} embeddings")
            return all_embeddings
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise
    
    def process_product(self, product: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process a single product and generate embeddings
        
        Args:
            product: Product dictionary
        
        Returns:
            List of dictionaries with chunk data and embeddings
        """
        try:
            # Prepare product text
            full_text = self.prepare_product_text(product)
            
            # Chunk the text
            chunks = self.chunk_text(full_text)
            
            if not chunks:
                logger.warning(f"No text to process for product {product.get('id')}")
                return []
            
            # Generate embeddings for all chunks
            embeddings = self.generate_embeddings(chunks)
            
            # Prepare result data
            result = []
            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                result.append({
                    'product_id': product['id'],
                    'chunk_id': idx,
                    'text': chunk,
                    'embedding': embedding
                })
            
            logger.info(f"Processed product {product['id']} into {len(result)} chunks")
            return result
        except Exception as e:
            logger.error(f"Failed to process product {product.get('id')}: {e}")
            raise
    
    def process_batch(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a batch of products
        
        Args:
            products: List of product dictionaries
        
        Returns:
            List of all chunk dictionaries with embeddings
        """
        all_results = []
        
        for product in products:
            try:
                results = self.process_product(product)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Failed to process product {product.get('id')}: {e}")
                continue
        
        return all_results

# Singleton instance
_processor = None

def get_processor() -> EmbeddingProcessor:
    """Get or create processor instance"""
    global _processor
    if _processor is None:
        _processor = EmbeddingProcessor()
    return _processor