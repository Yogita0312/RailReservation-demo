'''
from fastapi import FastAPI, Depends, Query
from sqlalchemy.orm import Session
from datetime import date
from database import SessionLocal, Base, engine
import crud
from schemas import SearchResponse, SearchRequest, TrainAvailability, ClassAvailability, BookingRequest, BookingSuccessResponse, BookingFailureResponse

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Railway Booking System")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/search_trains", response_model=list[TrainAvailability])
def search_trains(from_station_id: int = Query(...), to_station_id: int = Query(...), travel_date: date = Query(...), db: Session = Depends(get_db)):
    return crud.search_trains(db, from_station_id, to_station_id, travel_date)

@app.post("/book_ticket", response_model=BookingSuccessResponse | BookingFailureResponse)
def book_ticket(booking: BookingRequest, db: Session = Depends(get_db)):
    return crud.book_ticket(db, booking)
'''


'''
from fastapi import FastAPI, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from database import SessionLocal, Base, engine
import crud
from schemas import (
    SearchResponse,
    SearchRequest,
    TrainAvailability,
    ClassAvailability,
    BookingRequest,
    BookingSuccessResponse,
    BookingFailureResponse,
)
import models
# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Railway Booking System")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/search_trains", response_model=list[TrainAvailability])
def search_trains(
    from_station: str = Query(..., description="Source station name"),
    to_station: str = Query(..., description="Destination station name"),
    travel_date: date = Query(...),
    db: Session = Depends(get_db),
):
    trains = crud.search_trains(db, from_station, to_station, travel_date)
    if not trains:
        raise HTTPException(status_code=404, detail="No trains found for this route")
    return trains


@app.post("/book_ticket", response_model=BookingSuccessResponse | BookingFailureResponse)
def book_ticket(booking: BookingRequest, db: Session = Depends(get_db)):
    return crud.book_ticket(db, booking)
'''




'''
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
)

# ------------------- Create tables -------------------
Base.metadata.create_all(bind=engine)

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
@app.get("/search_trains", response_model=list[TrainAvailability])
def search_trains(
    from_station: str = Query(..., description="Source station name"),
    to_station: str = Query(..., description="Destination station name"),
    travel_date: date = Query(..., description="Date of journey"),
    db: Session = Depends(get_db)
):
    trains = crud.search_trains(db, from_station, to_station, travel_date)
    if not trains:
        raise HTTPException(status_code=404, detail="No trains found for this route")
    return trains


# ------------------- Book Ticket -------------------
@app.post(
    "/book_ticket",
    response_model=BookingSuccessResponse | BookingFailureResponse
)
def book_ticket(booking: BookingRequest, db: Session = Depends(get_db)):
    result = crud.book_ticket(db, booking)
    if isinstance(result, BookingFailureResponse):
        raise HTTPException(status_code=400, detail=result.message)
    return result
'''

'''
from fastapi import FastAPI, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from database import SessionLocal, Base, engine
import crud
from schemas import (
    TrainAvailability,
    BookingRequest,
    BookingSuccessResponse,
    BookingFailureResponse
)

# ------------------- Create tables -------------------
Base.metadata.create_all(bind=engine)

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
@app.get("/search_trains", response_model=list[TrainAvailability])
def search_trains(
    from_station: str = Query(..., description="Source station name"),
    to_station: str = Query(..., description="Destination station name"),
    travel_date: date = Query(..., description="Date of journey"),
    db: Session = Depends(get_db)
):
    trains = crud.search_trains(db, from_station, to_station, travel_date)
    if not trains:
        raise HTTPException(status_code=404, detail="No trains found for this route")
    return trains

# ------------------- Book Ticket -------------------
@app.post(
    "/book_ticket",
    response_model=BookingSuccessResponse | BookingFailureResponse
)
def book_ticket(booking: BookingRequest, db: Session = Depends(get_db)):
    result = crud.book_ticket(db, booking)
    if isinstance(result, BookingFailureResponse):
        raise HTTPException(status_code=400, detail=result.message)
    return result
'''


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
@app.get("/search_trains", response_model=list[TrainAvailability])
def search_trains(
    from_station: str = Query(..., description="Source station name"),
    to_station: str = Query(..., description="Destination station name"),
    travel_date: date = Query(..., description="Date of journey"),
    db: Session = Depends(get_db)
):
    trains = crud.search_trains(db, from_station, to_station, travel_date)
    if not trains:
        raise HTTPException(status_code=404, detail="No trains found for this route")
    return trains

# ------------------- Book Ticket -------------------
'''
@app.post(
    "/book_ticket",
    response_model=BookingSuccessResponse | BookingFailureResponse
)
def book_ticket(booking: BookingRequest, db: Session = Depends(get_db)):
    result = crud.book_ticket(db, booking)
    if isinstance(result, BookingFailureResponse):
        raise HTTPException(status_code=400, detail=result.message)
    return result
'''