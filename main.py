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
    train_name: str = Query(None, description="Name of the train"),
    train_number: str = Query(None, description="Train number"),
    train_type: str = Query(None, description="Train type"), 
    return_date: date = Query(None, description="Date of return journey"),
    return_time: str = Query(None, description="Time of return journey (HH:MM)"),
    return_train_class: str = Query(None, description="Train class preference for return journey"),
    return_train_number: str = Query(None, description="Train number for return journey"),
    return_train_name: str = Query(None, description="Name of the train for return journey"),
    return_train_type: str = Query(None, description="Train type for return journey"),
    db: Session = Depends(get_db)
):
    trains = crud.search_trains(
        db=db,
        from_station_name=from_station,
        to_station_name=to_station,
        travel_date=travel_date,
        train_class=train_class,
        time=time,
        return_date=return_date,
        return_time=return_time,
        train_name=train_name,
        train_number=train_number,
        train_type=train_type,
        return_train_class=return_train_class,
        return_train_number=return_train_number,
        return_train_name=return_train_name,
        return_train_type=return_train_type
    )
    if not trains:
        raise HTTPException(status_code=404, detail="No trains found for this route")
    return trains




