from google.cloud import firestore
import time
import json
from datetime import datetime

# Function to test Firestore integration
def test_firestore_integration():
    print("🔍 Testing Firestore integration with database 'agente-context-prueba'...")
    
    try:
        # Initialize Firestore client with specific database ID
        db = firestore.Client(
            project='diap3-458416',
            database='agente-context-prueba'  # Specify the database ID here
        )
        print("✅ Connected to Firestore successfully")
        
        # Create a test collection name with timestamp to avoid conflicts
        timestamp = int(time.time())
        test_collection = f"test_collection_{timestamp}"
        test_document = "test_session_id"
        
        print(f"📝 Creating test collection: {test_collection}")
        
        # Test 1: Write operation
        print("\n📋 TEST 1: Basic Write Operation")
        doc_ref = db.collection(test_collection).document(test_document)
        test_data = {
            "messages": [
                {"role": "user", "content": "Hola, necesito una dieta."},
                {"role": "assistant", "content": "¡Hola! Estaré encantado de ayudarte con una dieta."}
            ],
            "intolerances": ["lactosa"],
            "test_timestamp": firestore.SERVER_TIMESTAMP
        }
        
        # Write the data
        doc_ref.set(test_data)
        print("✅ Write operation successful")
        
        # Test 2: Read operation
        print("\n📋 TEST 2: Read Operation")
        doc = doc_ref.get()
        if doc.exists:
            result = doc.to_dict()
            print("✅ Read operation successful")
            print(f"📄 Retrieved data: {json.dumps(result, default=str, indent=2)}")
        else:
            print("❌ Document does not exist after writing!")
            return False
        
        # Test 3: Update operation
        print("\n📋 TEST 3: Update Operation")
        doc_ref.update({
            "messages": firestore.ArrayUnion([
                {"role": "user", "content": "¿Puedes darme una dieta baja en carbohidratos?"}
            ]),
            "diet_updated": True
        })
        print("✅ Update operation successful")
        
        # Verify update
        doc = doc_ref.get()
        if doc.exists:
            result = doc.to_dict()
            if len(result.get("messages", [])) == 3 and result.get("diet_updated") == True:
                print("✅ Update verification successful")
                print(f"📄 Updated data: {json.dumps(result, default=str, indent=2)}")
            else:
                print("❌ Update didn't apply correctly!")
                return False
        
        # Test 4: LangGraph FirestoreSaver compatibility
        print("\n📋 TEST 4: Data Structure Compatibility for LangGraph")
        state_data = {
            "messages": [
                {"role": "user", "content": "Quiero una dieta vegetariana"},
                {"role": "assistant", "content": "Perfecto, te recomiendo una dieta basada en legumbres."}
            ],
            "intolerances": [],
            "forbidden_foods": ["carne", "pescado"],
            "diet": {"breakfast": "Avena con frutas", "lunch": "Ensalada de garbanzos"},
            "budget": 100,
            "info_dietas": "Dieta vegetariana equilibrada",
            "grocery_list": ["avena", "frutas", "garbanzos"]
        }
        
        langgraph_doc = f"langgraph_test_{timestamp}"
        langgraph_ref = db.collection("conversations").document(langgraph_doc)
        langgraph_ref.set(state_data)
        
        # Verify LangGraph compatible data
        doc = langgraph_ref.get()
        if doc.exists:
            result = doc.to_dict()
            print("✅ LangGraph data structure test successful")
            print(f"📄 LangGraph data: {json.dumps(result, default=str, indent=2)}")
        else:
            print("❌ LangGraph data write failed!")
            return False
        
        # Clean up the test collections/documents
        print("\n🧹 Cleaning up test data...")
        doc_ref.delete()
        langgraph_ref.delete()
        print("✅ Cleanup successful")
        
        print("\n🎉 All Firestore tests passed successfully! Your service account is properly configured.")
        return True
        
    except Exception as e:
        print(f"❌ Error during Firestore testing: {str(e)}")
        print("\nPossible issues:")
        print("1. Make sure your service account has the 'Cloud Datastore User' role")
        print("2. Verify that Firestore is enabled in your project")
        print("3. Check that you're using the correct project ID and database ID")
        print("4. Ensure the database has been created and is ready")
        return False

if __name__ == "__main__":
    test_firestore_integration()