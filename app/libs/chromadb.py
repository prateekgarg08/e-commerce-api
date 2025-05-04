import chromadb
import sys
from chromadb.utils.embedding_functions import OpenCLIPEmbeddingFunction
client = chromadb.PersistentClient(path="embeddings")
import numpy
from app.db.database import db
from PIL import Image
import requests
import io
from chromadb.utils.embedding_functions import OpenCLIPEmbeddingFunction
embedding_function = OpenCLIPEmbeddingFunction(device="mps" if sys.platform == "darwin" else "cuda")
collection = client.get_or_create_collection(name="collections",embedding_function=embedding_function)

def fetchImage(url):
  response = requests.get(url)

  return io.BytesIO(response.content)
def add_image(id,url,metadata):
  collection.add(ids=[id],images=[numpy.array(Image.open(fetchImage(url)))],metadatas=[metadata])




def search_image(image,n_results=100):
  result =  collection.query(query_images=[image],n_results=n_results)
  print(result)
  return result["ids"][0]



  

async def update_metadata():
  cursor = db.products.find({})

  products = await cursor.to_list(None)

  ids = [str(product["_id"]) for product in products]
  images = [numpy.array(Image.open(fetchImage(product["images"][0]))) for product in products]
  metadatas =  [
    {
  "_id": str(product["_id"]),
  
  "price":product["price"],
  "category_id": product["category_id"]
}
  for product in products]


  collection.add(ids=ids,metadatas=metadatas,images=images)