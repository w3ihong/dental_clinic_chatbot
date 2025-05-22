from openai import OpenAI
import os
from dotenv import load_dotenv
from index import VectorStore
from booking import Booking
from booking import Bookings
import json
import datetime

load_dotenv()

def generate_response_w_RAG(store: VectorStore, prompt):

    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    rejection_message = "Sorry, I don't have enough information to answer that question. Please contact us at BrightSmile Dental Clinic for more information."

    rag_results = store.retrieve_docs(prompt)
    # print("Results from vector store: ", rag_results)
    if rag_results == "NIL":
        return rejection_message
    
    #refine the prompt
    dev_prompt = f"""
                    You are a helpful assistant for BrightSmile Dental Clinic. Your job is to help answer questions about the clinic and to set up appointments. 
                    When answering questions, use only what is provided in the context, do not infer, generalize, or assume any information. 
                    If no relavant information is provided, respond with '{rejection_message}'
                    Context: {rag_results}
                    """
    
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        store=True,
        messages = [
            {"role": "developer", "content": dev_prompt},
            {"role": "user", "content": prompt}
        ]
    )

    response = completion.choices[0].message.content
    return response

def process_booking(Bookings: Bookings):

    now = datetime.datetime.now()
    curr_date, curr_day  = now.date(), now.strftime("%A")

    def parse_input(input : str, input_type:str):
        # parse the name and time from the input
        client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        if input_type == "time":
            message = f"""
                        Given the provided input, extract the time of day.
                        Respond strictly in the following JSON format: {{"time": "HH"}}
                        - If no am or pm is indicated, assume the time falls between 9 AM and 5 PM.
                        - The time should be represented as a number between 0 and 23 (24-hour format, without minutes).
                        - If the input does not contain a valid or inferable time, set the value to false.
                        - Do not include any explanation or additional text in your response.

                        User input: "{input}"
                        """

            # message = f"""Extract the time from the following input, return the output in this format {{"time": "HH"}} 
            #             and nothing else. The time should be a number between 0-23. If time is not provided or cannot be 
            #             accurately derived, return false in place of the value.
            #             User input: "{input}"
            # #             """
        elif input_type == "name":
            message = f"""
                        Given the user's input, extract the user's name.
                        Respond strictly in the following JSON format: {{"name": "name"}}

                        - If either the name cannot be confidently determined, set its value to false.

                        User input: "{input}"
                        """
        elif input_type == "date":
            message = f"""
                        Given the user's input, extract the user's date of the appointment.
                        Respond strictly in the following JSON format:: {{"date": "YYYY-MM-DD"}}.
                        
                        - consider that inputs might be in DD/M
                        - If the date is incomplete or relative (e.g. "next Friday"), infer the full date based on today's date: {curr_date} ({curr_day}).
                        - The derived date must be strictly after {curr_date}.
                        - If the date cannot be confidently determined, set its value to false.

                        User input: "{input}"
                        """
        elif input_type == "name_date":

            message = f"""
                        Given the user's input, extract the user's name and selected date of the appointment.
                        Respond strictly in the following JSON format: {{"name": "name", "date": "YYYY-MM-DD"}}
                        
                        - consider that inputs might be in DD/M
                        - If the date is incomplete or relative (e.g. "next Friday"), infer the full date based on today's date: {curr_date} ({curr_day}).
                        - The derived date must be strictly after {curr_date}.
                        - If either the name or date cannot be confidently determined, set its value to false.

                        User input: "{input}"
                        """

        try:
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                store=True,
                messages = [
                    {"role": "system", "content": "You are an assistant that extracts structured information from natural language."},
                    {"role": "user", "content": message},
                ]
            )
        
            response = json.loads(completion.choices[0].message.content.strip("```json"))
            

        except Exception as e:
            print("Error in OpenAI API call: ", e)
            # print("Response from OpenAI: ", completion.choices[0].message.content)
            if input_type == "name" or input_type == "date" or input_type == "time":
                return False
            else:
                return False, False
        # print("Response from OpenAI: ", response)
        # parse the response
        if input_type == "time":
            try:
                time = response["time"] 
                return time
            except Exception as e:
                print("Error parsing response: ", e)
                return False
            
        if input_type == "name":
            try:
                name = response["name"]
                return name
            except Exception as e:
                print("Error parsing response: ", e)
                return False
        elif input_type == "date":
            try:
                date = response["date"]
                return date
            except Exception as e:
                print("Error parsing response: ", e)
                return False
        elif input_type == "name_date":
            try:
                name = response["name"]
                date = response["date"]
                
                return name, date
            except Exception as e:
                print("Error parsing response: ", e)
                return False, False
    

    def verify_date(date):
        # check if the date is in the future
        try:
            date_obj = datetime.datetime.strptime(date, "%Y-%m-%d").date()
            date_day = date_obj.strftime("%A")
            if date_obj < curr_date:
                return False, "Sorry, the date you provided is in the past. Please choose a future date."
            elif date_day == "Sunday":
                return False, "Sorry, we are closed on Sundays."
            else:
                return True,  "date available"
        except Exception as e:
            print("Error parsing date: ", e)
            return False, e

    name = False
    date = False
    time = False

    # get name, date, time and remarks
    # add error handling
    print("--" * 40)
    print("Assistant: Please tell me your name and preferred date.")
    name_date_input = input("You: ").strip()
    if name_date_input != "":
        name, date = parse_input(name_date_input, "name_date")
        verf, message = verify_date(date)
        if not verf:
            print("--" * 40)
            print(f"Assistant: {message}")
            date = False  # Reset date
            
    # name loop
    while name == False:
        print("--" * 40)
        print("Assistant: Sorry, I didn't get your name. Could you repeat it?")
        name_input = input("You: ")
        
        name = parse_input(name_input, "name")

    # Date loop - keep asking until we get a valid date with available slots
    date_found = False
    while not date_found:
        # First, ensure we have a valid date
        while date == False:
            print("--" * 40)
            print("Assistant: Can I have your preferred date for the appointment.")
            date_input = input("You: ").strip().lower()
            if date_input == "":
                print("Assistant: Please provide a valid date.")
                continue
            
            date = parse_input(date_input, "date")
            if date == False:
                print("Assistant: Sorry, I didn't get the date. Please try again.")
                continue
            verf, message = verify_date(date)
            if not verf:
                print("--" * 40)
                print(f"Assistant: {message}")
                date = False  # Reset date
                continue

        # Now check if the date has available slots
        avail = Bookings.get_available_slots(date)
        if len(avail) > 0:
            date_found = True
        else:
            print("--" * 40)
            print(f"Assistant: Sorry, there are no available slots for {date}. Please choose another date.")
            date = False  # Reset date 
            continue
    
        # Time slot selection loop
        time_selected = False
        while not time_selected:
            # Convert to 12hr format in str
            avail_str = [str(i) + " AM" if i < 12 else str(i - 12) + " PM" for i in avail]
            # Format output in 2 columns
            print("--" * 40)
            print(f"Here are the available time slots for {date}:")
            for i in range(0, len(avail_str), 2):
                if i + 1 < len(avail_str):
                    print(f"{avail_str[i]:<15} | {avail_str[i + 1]:<15}") 
                else:
                    print(f"{avail_str[i]:<15} | {' ':<15}")
            print(" ")
            print("Assistant: Please choose a time from the available slots or type \"back\" to choose another date.")
            
            time_input = input("You: ").strip().lower()
            if time_input == "":
                print("Assistant: Please provide a valid time.")
                continue
                
            if time_input == "back" or time_input == "go back" or time_input == "cancel":
                # Reset date selection to try another date
                date = False
                date_found = False
                # Go back to date selection loop
                break
                
            # Parse the time
            parsed_time = parse_input(time_input, "time")
            if parsed_time == False or parsed_time == "False":
                print("Assistant: Sorry, I didn't get the time. Please try again.")
                continue
            # Check if the time is valid
            if int(parsed_time) in avail:
                time_selected = True
                time = int(parsed_time)
            else:
                print("Assistant: Sorry, the time you selected is not available. Please choose another time slot.")
        
        # # If we went back to date selection, restart the date loop
        # if not time_selected:
        #     continue
    time_12hr = str(time) + " AM" if time < 12 else str(time - 12) + " PM"
    print(f"Assistant: Got it! {name}, Your appointment will be on {date} at {time_12hr}.")

    print("--" * 40)
    print("Assistant: Do you have any remarks or special requests that you would like us to know?")
    remarks = input("You: ")

    print("--" * 40)
    print("Booking Summary:")
    print(f"Name: {name}")
    print(f"Date: {date}")
    print(f"Time: {time_12hr}")
    print(f"Remarks: {remarks}")
    print(" ")
    print("Assistant: Please confirm your booking (yes/no).")

    confirm = input("You: ").strip().lower()
    if confirm == "yes" or confirm == "y" or confirm == "confirm":
        # save the booking
        b1 = Booking(name,date,time,remarks)
        if Bookings.add_booking(b1):
            if Bookings.save_bookings():
                print("--" * 40)
                print("Assistant: Your booking has been successfully made.")
                
        else:
            print("Error making booking.")
            
        
    else:
        print("--" * 40)
        print("Assistant: Booking cancelled.")
    
    print("--" * 40)
    print("           Do you have any additional queries or wish to set up an appointment?")
    print("Assistant: if not type 'exit' to quit.")
    return
    
def booking_trigger_check(input):
    # use openAI to determine if the input is a booking trigger
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    message = f"""
                You are a helpful assistant for BrightSmile Dental Clinic. Your job is to help answer questions about the clinic and to set up appointments.

                Given the user's input, determine if the user wants to book an appointment with us .
                Respond strictly in the following JSON format: {{"trigger": true or false}}

                User input: "{input}"
                """
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            store=True,
            messages = [
                {"role": "user", "content": message},
            ]
        )
    
        response = json.loads(completion.choices[0].message.content.strip("```json"))
        return response["trigger"]
    except Exception as e:
        print("Error in OpenAI API call: ", e)
        # print("Response from OpenAI: ", completion.choices[0].message.content)
        return False

def chat_loop(bookings : Bookings, store: VectorStore):
    booking_triggers = ["book", "appointment", "schedule"]
    print("--" * 40)
    print("Welcome to BrightSmile Dental Clinic!")
    print("I am your virtual assistant. I can help you with your queries and set up appointments.")
    print("Type 'exit' to quit.")
    while True:
        print("--" * 40)
        prompt = input("You: ")
        if prompt.lower() == "exit":
            break

        # Check if input contanins any booking triggers
        if any(trigger in prompt.lower() for trigger in booking_triggers) or prompt.lower() == "yes":
            if booking_trigger_check(prompt):
                print("--" * 40)
                print("Assistant: It seems like you want to book an appointment. Let me help you with that.")
                process_booking(bookings)
                continue
        

        response = generate_response_w_RAG(store, prompt)
        print("--" * 40)
        print("Assistant:", response)

def main():
    bookings_file = "bookings_sample.csv"
    bookings = Bookings(bookings_file)
    data_path = "data.jsonl"
    store_path = "faiss_knowledge_base"
    store = VectorStore(data_path, store_path)
    chat_loop(bookings, store)
    return
    
if __name__ == "__main__":
    main()