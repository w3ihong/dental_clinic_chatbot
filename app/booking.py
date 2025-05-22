import pandas as pd
import datetime

class Booking:
    def __init__(self, name, date, time, remarks = ""):
        self.name = name
        self.date = date
        self.time = time
        self.remarks = remarks

class Bookings:
    def __init__(self, file_path: str="bookings_sample.csv"):
        ##parse csv file
        self.bookings = self.load_bookings(file_path)
        self.file_path = file_path
    
    def load_bookings(self, file_path: str):
        df = pd.read_csv(file_path)
        return df.to_dict(orient='records')

    def save_bookings(self):
        try:
            df = pd.DataFrame(self.bookings)
            df.to_csv(self.file_path, index=False)
            return True
        except Exception as e:
            print(f"Error saving bookings: {e}")
            return False

    def add_booking(self, Booking :Booking):
        booking = {
            "name": Booking.name,
            "date": Booking.date,
            "time": Booking.time,
            "remarks": Booking.remarks
        }
        try:
            self.bookings.append(booking)
            return True
        except Exception as e:
            print(f"Error adding booking: {e}")
            return False

    def get_available_slots(self, date):
        # Weekday available slots are from 9 to 16 (9 AM to 4 PM)( 1 hours slots)(12 lunch break)
        # Saturday available slots are from 10 to 13 (9 AM to 1 PM)( 1 hours slots)(lunch break at 12)
        # no slots on Sunday

        # get the day of the week
        day = datetime.datetime.strptime(date, "%Y-%m-%d").weekday()
        if day == 6:  # Sunday
            return []
        if day == 5:  # Saturday
            available_slots = [10, 11, 13]
        else:  
            available_slots = [9, 10, 11, 13, 14, 15, 16]
        for booking in self.bookings:
            try:
                if booking['date'] == date:
                    available_slots.remove(int(booking['time']))
            except ValueError:
                print(f"Error removing booking time: {booking['time']} for date: {date}")
                continue

        return available_slots


def test():
    path = "bookings_sample.csv"
    bookings = Bookings(path)
    date = "2025-06-01"
    avail = bookings.get_available_slots(date)
    print(f"Available slots for {date}: {avail}")

if __name__ == "__main__":
    test()