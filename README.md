# Clinic chat-bot 
A CLI chat bot, utilizing openai as its core, its capabilities include:
1. Answering user questions based on a provided knowledge base.
2. Handles appointment booking (date, time, user name).
3. Log the appointment details in a local CSV file.

> **Note:** This project was developed on Windows. Issues arising from operating system differences may not be account for.

## Setup & Run
1. Clone the repository to your local machine
2. Add a `.env` file in the root directory with the following content:
``` 
OPENAI_API_KEY=your_openai_api_key
```
3. Execute `pip install -r requirements.txt`
4. Execute `python app/main.py` to start the chatbot

## Files
    app
    | -- booking.py
    | -- index.py
    | -- main.py
    faiss_knowledge_base
    .env
    bookings_sample.csv
    data.jsonl
    additional_KB.pdf
    KB.pdf
    README.md
    requirements.txt

- booking.py
    - contains booking and bookings class and associated functions
- index.py
    - contains VectorStore class, associated class functions and document retrieval
    - functions for pdf parsing and adding data to datafile
- main.py
    - main chat loop
- faiss_knowledge_base
    - generated FAISS index
- .env
    - add openai api key here
- bookings_sample.csv
    - output from bookings created by the chatbot, contians some sample data
- data.jsonl
    - knowledge base generated from provided pdf
- KB.pdf
    - pdf provided thru email for task
- additional_KB.pdf
    - contains data about the services offered by the clinic
    - data is parsed and added to the knowledge base
- README.md
- requirements.txt

## Approach and Design Choices


### Data Extraction 
- Text extracted from PDF using PyMuPDF
- Question/answer pairs generated with OpenAI (better performance than chunking for this use case)
- Data saved as JSONL file
- Additional data can be added with `add_PDF_to_KnowledgeBase` function in `index.py`
    - see main() in `index.py`

### Vector Store
- FAISS implementation for efficient similarity searches
- Vector store created from JSONL file
- Index saved locally for persistence, no need to recreate on each run
- Can be updated when knowledge base changes

### RAG (Retrieval-Augmented Generation)
- Retrieves top 5 matches from vector store with similarity threshold
- Out-of-scope queries are rejected when no relevant documents are found, saving compute 
- Retrieved documents are included in the generation prompt for context

### Bookings
- Initialized with data from "bookings_sample.csv"
- New bookings can be added and saved to the same file
- Availability checking for any day/date:
    - Respects working hours (9AM-5PM on weekdays, and 10AM-2PM on saturday)
    - Accounts for lunch break (12PM-1PM)
    - All appointments are 1 hour in duration

### Main Chat Loop
- Answers user queries based on retrieved documents
    - Rejects answering if no relevant documents are found
- Detects booking attempts using trigger words
    - Secondary intent verification with OpenAI (e.g., "I don't want to book" won't trigger booking sequence)
- Appointment booking workflow:
    - Robust input validation with re-prompting when needed
    - Accepts natural language inputs without requiring specific formats
        - Examples: "I'm Tommy, I want a booking for tomorrow" or "Johnny for 6th June"
    - Displays all available slots for selected date
    - Option to return to date selection if no suitable time slots available
    - Confirmation step before finalizing
    - Bookings saved to "bookings_sample.csv"






