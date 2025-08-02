#!/usr/bin/env python3
"""
Check if the local model is ready for Docker deployment
"""

import os
from pathlib import Path

def check_model():
    """Check if the local model exists and is accessible"""
    
    print("🔍 Checking local model for Docker deployment...")
    print("=" * 50)
    
    # Check if models directory exists
    models_dir = Path("models")
    if not models_dir.exists():
        print("❌ Models directory not found")
        print("💡 Run 'python download_model.py' to download the model")
        return False
    
    # Check if model exists
    model_path = models_dir / "all-MiniLM-L6-v2"
    if not model_path.exists():
        print("❌ Model directory not found")
        print(f"💡 Expected path: {model_path}")
        print("💡 Run 'python download_model.py' to download the model")
        return False
    
    # Check model files
    required_files = [
        "config.json",
        "pytorch_model.bin",
        "sentence_bert_config.json",
        "special_tokens_map.json",
        "tokenizer_config.json",
        "tokenizer.json",
        "vocab.txt"
    ]
    
    missing_files = []
    total_size = 0
    
    print("📁 Checking model files...")
    for file_name in required_files:
        file_path = model_path / file_name
        if file_path.exists():
            size_mb = file_path.stat().st_size / (1024 * 1024)
            total_size += size_mb
            print(f"   ✅ {file_name}: {size_mb:.1f} MB")
        else:
            missing_files.append(file_name)
            print(f"   ❌ {file_name}: MISSING")
    
    if missing_files:
        print(f"\n❌ Missing files: {', '.join(missing_files)}")
        print("💡 Model appears to be incomplete")
        return False
    
    print(f"\n✅ Model is complete!")
    print(f"📊 Total size: {total_size:.1f} MB")
    print(f"📁 Model location: {os.path.abspath(model_path)}")
    
    # Test model loading
    print("\n🧪 Testing model loading...")
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(str(model_path))
        test_text = "This is a test sentence."
        embedding = model.encode(test_text)
        print(f"✅ Model loads successfully!")
        print(f"📊 Embedding shape: {embedding.shape}")
        return True
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return False

def check_docker_ready():
    """Check if everything is ready for Docker"""
    
    print("\n🐳 Checking Docker readiness...")
    print("=" * 30)
    
    # Check if Docker files exist
    docker_files = ["Dockerfile", "docker-compose.yml"]
    for file_name in docker_files:
        if os.path.exists(file_name):
            print(f"✅ {file_name}")
        else:
            print(f"❌ {file_name} - MISSING")
            return False
    
    # Check if static files exist
    static_dir = Path("static")
    if static_dir.exists():
        html_files = list(static_dir.glob("*.html"))
        if html_files:
            print(f"✅ Static files ({len(html_files)} HTML files)")
        else:
            print("❌ No HTML files in static directory")
            return False
    else:
        print("❌ Static directory not found")
        return False
    
    # Check if main.py exists
    if os.path.exists("main.py"):
        print("✅ main.py")
    else:
        print("❌ main.py - MISSING")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Docker Model Checker")
    print("=" * 30)
    
    model_ok = check_model()
    docker_ok = check_docker_ready()
    
    print("\n" + "=" * 50)
    if model_ok and docker_ok:
        print("🎉 Everything is ready for Docker deployment!")
        print("\n💡 Next steps:")
        print("   1. Run: docker-compose up --build")
        print("   2. Open: http://localhost:8000")
        print("   3. Upload your CSV files and start searching!")
    else:
        print("❌ Some issues need to be fixed before Docker deployment")
        if not model_ok:
            print("   - Model needs to be downloaded")
        if not docker_ok:
            print("   - Docker files are missing") 