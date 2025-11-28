from pydantic import BaseModel, Field
from typing import List
from datetime import date, time
from typing import Optional



# ---------- Request Models ----------

class SearchRequest(BaseModel):
    from_station: str
    to_station: str
    travel_date: date
    return_date: Optional[str] = None
    train_name:  Optional[str] = None
    train_number:  Optional[str] = None
    train_class:  Optional[str] = None
    train_type: Optional[str] = None
    time:  Optional[str] = None

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
    train_number: int | None = None
    train_type: str | None = None
    from_station: str
    to_station: str
    departure_time: Optional[time] = None   # <- changed
    arrival_time: Optional[time] = None
    departure_date: Optional[date] = None
    classes: List[ClassAvailability]


class SearchResponse(BaseModel):
    onward: List[TrainAvailability]
    return_: List[TrainAvailability] = Field(..., alias="return")

    class Config:
        populate_by_name = True
        allow_population_by_field_name = True   

class RoundTripResponse(BaseModel):
    onward: List[TrainAvailability]
    return_trains: List[TrainAvailability]

