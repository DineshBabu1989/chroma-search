from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
import uvicorn
import os
import pandas as pd
import chromadb
from sentence_transformers import SentenceTransformer
import uuid
from typing import List, Dict, Any
import json

app = FastAPI(title="Bosch Brakes Search", version="1.0.0")

# Mount static files only if directory exists
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize ChromaDB client
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# Initialize sentence transformer model from local directory
try:
    model_path = "models/all-MiniLM-L6-v2"
    if os.path.exists(model_path):
        embedding_model = SentenceTransformer(model_path)
        print("✅ Local sentence transformer model loaded successfully")
        print(f"📁 Model location: {os.path.abspath(model_path)}")
    else:
        print(f"⚠️  Local model not found at: {model_path}")
        print("💡 Using fallback to download model...")
        # Fallback to downloading if local model doesn't exist
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Sentence transformer model downloaded and loaded successfully")
except Exception as e:
    print(f"❌ Error loading sentence transformer model: {e}")
    print("💡 Make sure the model is available in the models/ directory")
    print("💡 Or run 'python download_model.py' to download the model locally")
    embedding_model = None

@app.get("/", response_class=HTMLResponse)
async def chat_page():
    return FileResponse("static/chat.html")

@app.get("/upload", response_class=HTMLResponse)
async def upload_page():
    return FileResponse("static/upload.html")

@app.post("/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    message = data.get("message", "")
    
    if not message:
        return {"response": "Please provide a message to search."}
    
    if not embedding_model:
        return {"response": "Embedding model not loaded. Please check the server logs."}
    
    # Get the collection name from the request (default to first available)
    collection_name = data.get("collection", None)
    
    try:
        # Get available collections
        collections = chroma_client.list_collections()
        
        if not collections:
            return {"response": "No data collections available. Please upload a CSV file first."}
        
        # Use specified collection or first available
        if not collection_name:
            collection_name = collections[0].name
        
        # Get the collection
        collection = chroma_client.get_collection(name=collection_name)
        
        # Convert query to embedding
        query_embedding = embedding_model.encode([message]).tolist()[0]
        
        # Search in ChromaDB
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=5,
            include=['documents', 'metadatas', 'distances']
        )
        
        if not results['documents'] or not results['documents'][0]:
            return {"response": "No relevant results found for your query."}
        
        # Format the response
        response_parts = []
        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0], 
            results['metadatas'][0], 
            results['distances'][0]
        )):
            similarity = 1 - distance  # Convert distance to similarity
            response_parts.append(f"**Result {i+1}** (Similarity: {similarity:.2%})\n{doc}")
            
            # Add metadata if available
            if metadata:
                metadata_str = ", ".join([f"{k}: {v}" for k, v in metadata.items() if k != 'Object_Text'])
                if metadata_str:
                    response_parts.append(f"Additional info: {metadata_str}")
            
            response_parts.append("")  # Add spacing
        
        return {"response": "\n".join(response_parts)}
        
    except Exception as e:
        return {"response": f"Error searching: {str(e)}"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    
    if not embedding_model:
        raise HTTPException(status_code=500, detail="Embedding model not loaded")
    
    try:
        # Read CSV file
        df = pd.read_csv(file.file)
        
        # Check if Object_Text column exists
        if 'Object_Text' not in df.columns:
            raise HTTPException(status_code=400, detail="CSV must contain 'Object_Text' column")
        
        # Generate collection name from filename
        collection_name = file.filename.replace('.csv', '').replace(' ', '_').lower()
        
        # Create or get collection
        try:
            collection = chroma_client.create_collection(name=collection_name)
        except:
            collection = chroma_client.get_collection(name=collection_name)
        
        # Process data in batches
        batch_size = 100
        total_records = len(df)
        processed_records = 0
        
        for i in range(0, total_records, batch_size):
            batch_df = df.iloc[i:i+batch_size]
            
            # Prepare documents and metadata
            documents = []
            metadatas = []
            ids = []
            
            for _, row in batch_df.iterrows():
                # Convert row to metadata (excluding Object_Text)
                metadata = {col: str(val) for col, val in row.items() if col != 'Object_Text' and pd.notna(val)}
                
                documents.append(str(row['Object_Text']))
                metadatas.append(metadata)
                ids.append(str(uuid.uuid4()))
            
            # Generate embeddings
            embeddings = embedding_model.encode(documents).tolist()
            
            # Add to collection
            collection.add(
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            processed_records += len(batch_df)
        
        return {
            "collection_name": collection_name,
            "count": total_records,
            "message": f"Successfully uploaded {total_records} records to collection '{collection_name}'"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.get("/collections")
async def get_collections():
    try:
        collections = chroma_client.list_collections()
        result = []
        
        for collection in collections:
            count = collection.count()
            result.append({
                "name": collection.name,
                "count": count
            })
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting collections: {str(e)}")

@app.delete("/collections/{collection_name}")
async def delete_collection(collection_name: str):
    try:
        chroma_client.delete_collection(name=collection_name)
        return {"message": f"Collection '{collection_name}' deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting collection: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 