from pydantic import BaseModel
from typing import List
from datetime import date, time
from typing import Optional



# ---------- Request Models ----------

class SearchRequest(BaseModel):
    from_station: str
    to_station: str
    travel_date: date

class PassengerInfo(BaseModel):
    name: str
    gender: str
    age: int

class BookingRequest(BaseModel):
    train_name: str
    travel_date: date
    travel_class: str
    contact_info: str
    passengers: List[PassengerInfo]


# ---------- Response Models ----------

class BookingSuccessResponse(BaseModel):
    status: str
    train_name: str
    train_no: int
    travel_date: date
    class_type: str
    ticket_price: float
    passengers: int
    total_price: float


class BookingFailureResponse(BaseModel):
    status: str = "failure"
    train_name: Optional[str] = None
    train_no: Optional[str] = None
    travel_date: Optional[date] = None
    message: str



class ClassAvailability(BaseModel):
    class_type: str
    total_berths: int
    booked: int
    available: int
    price: float


class TrainAvailability(BaseModel):
    #train_no: int
    train_name: str
    from_station: str
    to_station: str
    departure_time: time
    arrival_time: time
    classes: List[ClassAvailability]


class SearchResponse(BaseModel):
    trains: List[TrainAvailability]
