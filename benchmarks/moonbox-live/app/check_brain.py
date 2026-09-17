
import asyncio
import logging
from services.mildlyawesome.brain import brain

# Setup concise logging
logging.basicConfig(level=logging.WARNING)

async def main():
    print("🧠 Testing Brain Service (Semantic Recall)...")
    try:
        # recall uses dummy embedding, so it relies on existing vectors in DB
        thoughts = await brain.recall("verify mildlyawesome", limit=3)
        print(f"✅ Recall executed successfully. Retrieved {len(thoughts)} thoughts.")
        
        if thoughts:
            print("   Sample contexts:")
            for i, t in enumerate(thoughts):
                print(f"   {i+1}. [{t.confidence}] {t.context[:60]}...")
        else:
            print("   (No thoughts found - DB might be empty, but connectivity is good)")
            
    except Exception as e:
        print(f"❌ Brain test failed: {e}")
        exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
