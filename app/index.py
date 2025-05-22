
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document
import fitz
import os
from dotenv import load_dotenv
from openai import OpenAI
import json

load_dotenv()

class VectorStore:
    def __init__(self, data_path: str, store_path: str=None, out_path: str="faiss_knowledge_base"):
        """
        Initialize the VectorStore.
        data_path: path to the jsonl file containing data for vector store creation
        store_path: path to the FAISS index file
            optional, if not provided, a new index will be created from data_path
        out_path: path to save the FAISS index file
            optional, default is "faiss_knowledge_base"
        """
        self.embed_model = OpenAIEmbeddings(
            model="text-embedding-ada-002"
        )
        self.out_path = out_path
        if store_path is None:
            self.vector_store = self.create_vector_store(data_path)
        else:
            self.vector_store = FAISS.load_local(store_path, self.embed_model, allow_dangerous_deserialization=True)

    def create_vector_store(self, path:str):
        '''
        Create a vector store from the data in the jsonl file.
        '''
        data = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"Skipping invalid line: {line.strip()} - Error: {e}")
                    continue  # Skip malformed lines

        # Convert data into LangChain Document format
        documents = [Document(page_content=item["input"], metadata={"output": item["output"]}) for item in data]
        # Create FAISS vector store
        vector_store = FAISS.from_documents(documents, self.embed_model)
        # Save FAISS index
        vector_store.save_local(self.out_path)
        return FAISS.load_local(self.out_path, self.embed_model, allow_dangerous_deserialization=True)

    def retrieve_docs(self,query:str, top_k:int =5, threshold:float= 0.8):
        '''
        Retrieve top k documents from the vector store based on the query.
        then filter with threshold.
        '''
        docs = self.vector_store.similarity_search_with_score(query, top_k)

        results = ""

        for doc in docs:
            if doc[1] < threshold:
                results += f" {doc[0].metadata['output']}\n"
        ## if there are no results, we know that the query is not relevant
        return results if results else "NIL"

# not class functions
def parse_pdf(file_path: str):
    '''
    Parse the PDF file and extract text from each page.
    '''
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    print(text)
    return text

def generate_in_out_pairs(text :str):
    '''
    Generate input/output pairs in json format based on the text provided and write to a jsonl file.

    text: the text to generate input/output pairs from
    count: the number of input/output pairs to generate
        optional, if not provided, count is determined by the model 
    '''
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
    )


    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        store=True,
        messages=[
            {"role": "user", "content": 
             f"""You are an AI assistant tasked with generating question-answer pairs from a given text.

                Using only the information provided in the context, generate a list of input/output pairs in the following JSON format:
                {{"input": "Question?", "output": "Answer"}}.

                - The "input" should be a natural-language question that can be answered using the text.
                - The "output" must be an accurate and complete answer, directly derived from the context.
                - Cover all facts and details found in the context by generating at least 2 distinct pairs for each fact/detail.
                - Do not infer or assume information beyond what is explicitly stated.
                - Your response should be a JSON array of such objects, and contain nothing else.

                Context:
                {text}
                """
            }
        ]
    )
    data = json.loads(completion.choices[0].message.content.strip("```json"))
    return data

def add_to_file(file_path: str, data: json):
    '''
    takes in json objecta and writes to file
    '''
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            for item in data:
                json_line = json.dumps(item)
                f.write(json_line + "\n")
            return True
    except Exception as e:
        print(f"""Error writing line to file: 
              Error: {e}
              line: {item}""")
        return False

def add_PDF_to_KnowledgeBase(file_path: str, data_path: str):
    '''
    takes in a pdf file and generates input/output pairs
    then adds them to the knowledge base
    '''
    pdf_text = parse_pdf(file_path)
    data = generate_in_out_pairs(pdf_text)
    if add_to_file(data_path, data):
        print("Data added to file successfully.")
    else:
        print("Failed to add data to file.")

    store = VectorStore(data_path)
    print("Vector store updated")

    return store

def main():
    # pdf you would like to add to the knowledge base
    file_path = "additional_KB.pdf"
    # path to the jsonl file where the data will be stored
    # there is existing data in "data.jsonl" file, from provided pdf
    data_path = "data.jsonl"

    store = add_PDF_to_KnowledgeBase(file_path, data_path)

    # retrieval test
    query = "tell me about the rool canal procedure?"
    print(store.retrieve_docs(query))


if __name__ == "__main__":
    main()

