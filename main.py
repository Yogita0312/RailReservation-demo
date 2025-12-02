from fastapi import FastAPI, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from database import SessionLocal, Base, engine
import crud
from schemas import (
    TrainAvailability,
    BookingRequest,
    BookingSuccessResponse,
    BookingFailureResponse,
    SearchResponse
)

# ------------------- Create tables -------------------
#Base.metadata.create_all(bind=engine)

# ------------------- FastAPI app -------------------
app = FastAPI(title="Railway Booking System")

# ------------------- Dependency -------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ------------------- Search Trains -------------------
@app.get("/search_trains", response_model= SearchResponse)
def search_trains(
    from_station: str = Query(..., description="Source station name"),
    to_station: str = Query(..., description="Destination station name"),
    travel_date: date = Query(..., description="Date of journey"),
    train_class: str = Query(..., description="Train class preference"),
    time: str= Query(..., description="Train time (HH:MM)"),
    return_date: date = Query(None, description="Date of return journey"),
    return_time: str = Query(None, description="Time of return journey (HH:MM)"),
    train_name: str = Query(None, description="Name of the train"),
    train_number: str = Query(None, description="Train number"),
    train_type: str = Query(None, description="Train type"), 
    db: Session = Depends(get_db)
):
    trains = crud.search_trains(db, from_station, to_station, travel_date, train_class, time, return_date, return_time, train_name, train_number, train_type)
    if not trains:
        raise HTTPException(status_code=404, detail="No trains found for this route")
    return trains




